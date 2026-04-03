from fastapi import APIRouter, Depends
from typing import List
from ....models.schemas import UserPublic, ChatRequest, ChatSession, ChatSessionCreate
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
    """General purpose chat with Gemini."""
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

@router.get("/sessions", response_model=List[ChatSession])
async def get_sessions(current_user: UserPublic = Depends(get_current_user)):
    """List all chat sessions for the current user."""
    return await ai_service.get_user_sessions(current_user.id)

@router.post("/sessions")
async def create_session(
    data: ChatSessionCreate, 
    current_user: UserPublic = Depends(get_current_user)
):
    """Start a new chat session."""
    session_id = await ai_service.create_chat_session(current_user.id, data.title)
    return {"session_id": session_id}

@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: str, 
    current_user: UserPublic = Depends(get_current_user)
):
    """Load messages for an existing session."""
    messages = await ai_service.get_session_history(session_id, current_user.id)
    if not messages and session_id != "new": # Allow empty for new but prevent unauthorized access
         # We could be more explicit with a 403, but get_session_history returns [] on no session
         pass
    return {"messages": messages}

@router.post("/sessions/{session_id}/messages")
async def add_message_to_session(
    session_id: str,
    message: dict, 
    current_user: UserPublic = Depends(get_current_user)
):
    """Send a message, save both to history, and get AI response."""
    # 1. Save user message (this also verifies ownership)
    await ai_service.save_chat_message(session_id, current_user.id, message)
    
    # 2. Get full history for context
    history = await ai_service.get_session_history(session_id, current_user.id)
    
    if not history:
        # This means the session didn't belong to the user or didn't exist
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Unauthorized access to this chat session")
    
    # 3. Add system prompt
    messages = list(history)
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {
            "role": "system", 
            "content": "You are PrepAI, a helpful tutor for NEET and JEE students. Answer their questions accurately and concisely."
        })
    
    # 4. Call AI
    response = await ai_service.chat_with_ai(messages)
    
    # 5. Save AI response
    assistant_msg = {"role": "assistant", "content": response}
    await ai_service.save_chat_message(session_id, current_user.id, assistant_msg)
    
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
