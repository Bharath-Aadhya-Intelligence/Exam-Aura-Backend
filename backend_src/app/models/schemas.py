from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# Onboarding Models
class OnboardingData(BaseModel):
    selected_exam: str
    exam_date: Optional[datetime] = None
    confidence_level: float
    study_styles: List[str]

# User Models
class UserBase(BaseModel):
    email: EmailStr
    name: str
    profile_photo: Optional[str] = None
    profile: Optional[OnboardingData] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserInDB(UserBase):
    hashed_password: str
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserPublic(UserBase):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Auth Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

# MCQ Models
class MCQQuestion(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    subject: str
    topic: str
    question_text: str
    options: List[str]
    correct_option_index: int
    explanation: str

class SessionSubmit(BaseModel):
    question_ids: List[str]
    answers: List[int]

class PracticeSession(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    questions: List[MCQQuestion]
    score: int = 0
    completed: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)
