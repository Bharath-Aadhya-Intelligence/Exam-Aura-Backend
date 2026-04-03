from fastapi import APIRouter, Depends
from typing import List
from backend_src.app.models.schemas import UserPublic, MCQQuestion, SessionSubmit
from backend_src.app.core.deps import get_current_user
from backend_src.app.services import mcq_service

router = APIRouter()

@router.get("/daily-questions", response_model=List[MCQQuestion])
async def get_daily_questions(
    category: str = None,
    current_user: UserPublic = Depends(get_current_user)
):
    return await mcq_service.get_daily_questions(current_user.id, category=category)

@router.post("/submit-session")
async def submit_session(
    data: SessionSubmit, 
    current_user: UserPublic = Depends(get_current_user)
):
    return await mcq_service.submit_session(
        current_user.id, data.question_ids, data.answers
    )
