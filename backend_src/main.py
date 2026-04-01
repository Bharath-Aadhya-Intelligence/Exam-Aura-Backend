from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta, datetime
from typing import List
from .auth import create_access_token, verify_password, get_current_user
from .models import UserCreate, UserPublic, Token, MCQQuestion
from .services import user_service, mcq_service, ai_service
from .config import get_settings

app = FastAPI(title="PrepAI API")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register", response_model=UserPublic)
async def register(user: UserCreate):
    existing_user = await user_service.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await user_service.create_user(user)

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await user_service.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserPublic)
async def read_users_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user

@app.get("/daily-questions", response_model=List[MCQQuestion])
async def get_daily_questions(current_user: UserPublic = Depends(get_current_user)):
    return await mcq_service.get_daily_questions(current_user.id)

@app.post("/submit-session")
async def submit_session(
    data: dict, 
    current_user: UserPublic = Depends(get_current_user)
):
    return await mcq_service.submit_session(
        current_user.id, data.get("question_ids"), data.get("answers")
    )

@app.post("/explain-ai")
async def explain_ai(
    data: dict, 
    current_user: UserPublic = Depends(get_current_user)
):
    return await ai_service.get_ai_explanation(
        data.get("question_text"), 
        data.get("student_answer"), 
        data.get("correct_answer")
    )

@app.get("/")
async def root():
    return {"message": "Welcome to PrepAI API"}
