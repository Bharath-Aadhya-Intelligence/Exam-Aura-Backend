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
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # AI & RAG Settings
    FAISS_INDEX_PATH: str = "data/vector_db/ncert_index"
    NCERT_DOCS_PATH: str = "data/ncert_corpus/"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
