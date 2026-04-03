from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    MONGODB_URL: str
    DATABASE_NAME: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # AI Configuration
    GEMINI_API_KEY: str = ""
    
    # AI & RAG Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    FAISS_INDEX_PATH: str = "data/vector_db/ncert_index"
    NCERT_DOCS_PATH: str = "data/ncert_corpus/"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
