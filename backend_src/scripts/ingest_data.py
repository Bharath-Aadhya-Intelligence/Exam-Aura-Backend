import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import faiss
import numpy as np
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings
from app.db.mongodb import get_database
import asyncio

settings = get_settings()

async def ingest_json(file_path: str, limit: int = 2000):
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

async def ingest_jsonl(file_path: str, limit: int = 2000):
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

async def process_chunks(chunks: list, source: str, subject: str):
    """Embed chunks and save to FAISS/MongoDB."""
    print(f"Processing {len(chunks)} chunks for {subject}...")
    
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    embeddings = model.encode(chunks)
    
    # 1. FAISS Indexing (Incremental/Fresh)
    # Note: In a real app, you'd add to an existing index. 
    # For now, we'll follow the pattern of creating a fresh index for the combined knowledge.
    index_path = f"{settings.FAISS_INDEX_PATH}.index"
    
    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
    else:
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
    
    start_index = index.ntotal
    index.add(embeddings.astype('float32'))
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    
    # 2. Saving to MongoDB
    db = get_database()
    chunk_docs = [
        {"index": start_index + i, "text": chunk, "source": source, "subject": subject}
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
