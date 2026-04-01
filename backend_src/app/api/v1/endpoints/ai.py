from fastapi import APIRouter, Depends
from ....models.schemas import UserPublic
from ....core.deps import get_current_user
from ....services import ai_service

router = APIRouter()

@router.post("/explain")
async def explain_ai(
    data: dict, 
    current_user: UserPublic = Depends(get_current_user)
):
    return await ai_service.get_ai_explanation(
        data.get("question_text"), 
        data.get("student_answer"), 
        data.get("correct_answer")
    )
