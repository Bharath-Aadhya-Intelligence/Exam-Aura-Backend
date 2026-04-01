from fastapi import APIRouter, Depends
from typing import List
from ....models.schemas import UserPublic, MCQQuestion
from ....core.deps import get_current_user
from ....services import mcq_service

router = APIRouter()

@router.get("/daily-questions", response_model=List[MCQQuestion])
async def get_daily_questions(current_user: UserPublic = Depends(get_current_user)):
    return await mcq_service.get_daily_questions(current_user.id)

@router.post("/submit-session")
async def submit_session(
    data: dict, 
    current_user: UserPublic = Depends(get_current_user)
):
    return await mcq_service.submit_session(
        current_user.id, data.get("question_ids"), data.get("answers")
    )
