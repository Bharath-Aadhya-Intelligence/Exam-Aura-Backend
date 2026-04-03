from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend_src.app.api.v1.api_router import api_router

app = FastAPI(title="PrepAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to Exam Aura API v1 (Version 2.x - Gemini Ironclad)"}
