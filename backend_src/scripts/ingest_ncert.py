import os
import faiss
import numpy as np
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings
from app.db.mongodb import get_database
import asyncio

settings = get_settings()

async def ingest_ncert(pdf_path: str):
    """Extract text from PDF, chunk it, and add to FAISS index."""
    print(f"Ingesting: {pdf_path}")
    
    # 1. Extract Text
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    
    # 2. Chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_text(text)
    print(f"Created {len(chunks)} chunks.")
    
    # 3. Embedding
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    embeddings = model.encode(chunks)
    
    # 4. Building FAISS Index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype('float32'))
    
    # 5. Saving Vector Index
    os.makedirs(os.path.dirname(settings.FAISS_INDEX_PATH), exist_ok=True)
    faiss.write_index(index, f"{settings.FAISS_INDEX_PATH}.index")
    
    # 6. Save chunk text to MongoDB (Production)
    db = get_database()
    chunk_docs = [
        {"index": i, "text": chunk, "source": pdf_path, "subject": "NCERT"}
        for i, chunk in enumerate(chunks)
    ]
    
    # Clear old chunks for this file if re-ingesting
    await db["ncert_chunks"].delete_many({"source": pdf_path})
    await db["ncert_chunks"].insert_many(chunk_docs)
            
    print(f"Ingestion complete! Added {len(chunks)} chunks to MongoDB.")

def create_mock_index():
    """Create a small dummy index for testing RAG flow."""
    print("Creating mock index...")
    chunks = [
        "Newton's First Law states that an object will remain at rest unless acted upon by a force.",
        "The Second Law defines force as mass times acceleration (F=ma).",
        "The Third Law says for every action there is an equal and opposite reaction.",
        "Ionic bonding is the complete transfer of valence electron(s) between atoms.",
        "Covalent bonding involves the sharing of electron pairs between atoms."
    ]
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    embeddings = model.encode(chunks)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype('float32'))
    
    os.makedirs(os.path.dirname(settings.FAISS_INDEX_PATH), exist_ok=True)
    faiss.write_index(index, f"{settings.FAISS_INDEX_PATH}.index")
    
    with open(f"{settings.FAISS_INDEX_PATH}_chunks.txt", "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk + "\n")
    print("Mock index created!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(ingest_ncert(sys.argv[1]))
    else:
        # For mock, we'll just print a warning that mock is disabled for production plans
        print("Please provide a PDF path to ingest for production.")
