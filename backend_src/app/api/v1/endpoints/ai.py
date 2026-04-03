from fastapi import APIRouter, Depends
from typing import List
from ....models.schemas import UserPublic, ChatRequest
from ....core.deps import get_current_user
from ....services import ai_service
from ....db.mongodb import ping_database

router = APIRouter()

@router.post("/explain")
async def explain_ai(
    data: dict, 
    current_user: UserPublic = Depends(get_current_user)
):
    """Explains an MCQ question using context from NCERT."""
    explanation = await ai_service.get_ai_explanation(
        data.get("question_text", ""), 
        data.get("student_answer", ""), 
        data.get("correct_answer", ""),
        user_profile=current_user.profile.dict() if current_user.profile else None
    )
    return {"explanation": explanation}

@router.post("/chat")
async def chat_ai(
    request: ChatRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """General purpose chat with Phi-3 personalization."""
    # Convert Pydantic models to dicts for the service
    messages = [msg.dict() for msg in request.messages]
    
    # Add a system prompt if not present to ensure it stays in character for PrepAI
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {
            "role": "system", 
            "content": "You are PrepAI, a helpful tutor for NEET and JEE students. Answer their questions accurately and concisely."
        })
        
    response = await ai_service.chat_with_ai(messages)
    return {"message": response}

@router.get("/status")
async def get_system_status():
    """Diagnostic endpoint for AI and DB connectivity."""
    ai_status = await ai_service.check_model_status()
    db_alive = await ping_database()
    
    return {
        "status": "online" if (ai_status["reachable"] and db_alive) else "degraded",
        "mongodb": "connected" if db_alive else "disconnected",
        "ai_model": ai_status
    }
