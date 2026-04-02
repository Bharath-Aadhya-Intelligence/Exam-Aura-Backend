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
    """Explains an MCQ question, with optional context history."""
    explanation = await ai_service.get_ai_explanation(
        data.get("question_text"), 
        data.get("student_answer"), 
        data.get("correct_answer"),
        data.get("history")
    )
    return {"explanation": explanation}

@router.post("/chat")
async def chat_ai(
    data: dict,
    current_user: UserPublic = Depends(get_current_user)
):
    """General purpose chat with history."""
    messages = data.get("messages", [])
    if not messages:
        return {"response": "Hi! I'm Exam Aura. How can I help you today?"}
        
    response = await ai_service.get_chatbot_response(messages)
    return {"response": response}
