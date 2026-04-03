import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import faiss
import numpy as np
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import get_settings
from app.db.mongodb import get_database
import asyncio

settings = get_settings()

async def ingest_json(file_path: str, limit: int = 1000):
    """Ingest JEE questions from JSON file."""
    print(f"Ingesting JSON: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Assuming data is a list of objects
    items = data[:limit]
    chunks = []
    
    for item in items:
        # Extract question and explanation text
        text = f"Question: {item.get('question_text', '')}\nExplanation: {item.get('explanation', '')}"
        chunks.append(text)
    
    await process_chunks(chunks, file_path, "JEE")

async def ingest_jsonl(file_path: str, limit: int = 1000):
    """Ingest NEET training data from JSONL file."""
    print(f"Ingesting JSONL: {file_path}")
    chunks = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            item = json.loads(line)
            # Assuming JSONL has 'text' or similar field
            text = item.get('text', str(item))
            chunks.append(text)
    
    await process_chunks(chunks, file_path, "NEET")

import google.generativeai as genai

async def get_gemini_embeddings(text: str) -> list:
    """Get embeddings using Google's Cloud Embedding API."""
    try:
        result = await genai.embed_content_async(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document",
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding Error: {e}")
        return [0.0] * 768

async def process_chunks(chunks: list, source: str, subject: str):
    """Embed chunks and save to FAISS/MongoDB."""
    print(f"Processing {len(chunks)} chunks for {subject} with Gemini Embeddings...")
    
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is missing!")
        return

    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    embeddings = []
    import asyncio
    
    for i, chunk in enumerate(chunks):
        retry_count = 0
        while retry_count < 3:
            try:
                emb = await get_gemini_embeddings(chunk)
                embeddings.append(emb)
                break
            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit, waiting 30s... (Retry {retry_count+1}/3)")
                    await asyncio.sleep(30)
                    retry_count += 1
                else:
                    raise e
        
        # Small delay to stay under RPM
        await asyncio.sleep(0.6)
        
        if (i+1) % 100 == 0:
            print(f"Embedded {i+1}/{len(chunks)} chunks...")
            
    embeddings_np = np.array(embeddings).astype('float32')
    
    # 1. FAISS Indexing
    index_path = f"{settings.FAISS_INDEX_PATH}.index"
    dimension = 768 # gemini-embedding-001
    
    # Always create fresh index for this migration or handle dimension change
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)
    
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    
    # 2. Saving to MongoDB
    db = get_database()
    chunk_docs = [
        {"index": i, "text": chunk, "source": source, "subject": subject}
        for i, chunk in enumerate(chunks)
    ]
    
    # Clear old chunks for this source if re-ingesting
    await db["ncert_chunks"].delete_many({"source": source})
    await db["ncert_chunks"].insert_many(chunk_docs)
    
    print(f"Ingestion complete for {subject}! Added {len(chunks)} chunks.")

if __name__ == "__main__":
    import sys
    loop = asyncio.get_event_loop()
    
    # Example usage: python ingest_data.py /path/to/jee.json /path/to/neet.jsonl
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            if path.endswith('.json'):
                loop.run_until_complete(ingest_json(path))
            elif path.endswith('.jsonl'):
                loop.run_until_complete(ingest_jsonl(path))
            else:
                print(f"Unsupported file format: {path}")
    else:
        print("Please provide paths to JSON or JSONL files.")
