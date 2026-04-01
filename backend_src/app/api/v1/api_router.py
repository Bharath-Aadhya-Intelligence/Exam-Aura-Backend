from fastapi import APIRouter
from .endpoints import auth, users, mcqs, ai

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(mcqs.router, prefix="/mcqs", tags=["MCQs"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
