import httpx
import json
import os
from typing import List, Dict, Any, Optional
from ..core.config import get_settings
from ..db.mongodb import get_database

# New imports for RAG
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError:
    faiss = None
    SentenceTransformer = None

import google.generativeai as genai

settings = get_settings()

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

# Initialize Embedding Model (Lazy Loading) - NO LONGER NEEDED FOR LOCAL
# Now using Google Cloud Embeddings

async def get_embeddings(text: str) -> np.ndarray:
    """Get embeddings using Google's Cloud Embedding API."""
    try:
        result = await genai.embed_content_async(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_query",
        )
        # Gemini returns a list, convert to numpy array
        return np.array([result['embedding']])
    except Exception as e:
        print(f"Embedding Error: {e}")
        return np.zeros((1, 768)) # gemini-embedding-001 is 768

async def call_gemini(messages: List[Dict[str, str]]) -> str:
    if not settings.GEMINI_API_KEY:
        return "AI Error: Gemini API Key is missing. Please add it to your .env file."
    
    # Standardize messages for Gemini format
    gemini_contents = []
    
    # Gemini REST API expects contents: [{"role": "user", "parts": [{"text": "..."}]}]
    # NOTE: System instruction should be special, but for direct REST we can prepend or use system_instruction field
    system_prompt = ""
    for msg in messages:
        if msg['role'] == 'system':
            system_prompt = msg['content']
        else:
            role = 'user' if msg['role'] == 'user' else 'model'
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg['content']}]
            })
            
    if system_prompt and gemini_contents:
        # Prepend system prompt to the first user message for simplicity and reliability
        original_text = gemini_contents[0]["parts"][0]["text"]
        gemini_contents[0]["parts"][0]["text"] = f"Instructions: {system_prompt}\n\nUser Question: {original_text}"

    # Try models confirmed as available for this key
    models_to_try = [
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash-lite-001',
        'gemini-1.5-flash',
        'gemini-pro'
    ]
    
    import httpx
    last_error = ""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for m_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1/models/{m_name}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {"contents": gemini_contents}
                
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    continue
            except Exception as e:
                last_error = str(e)
                continue
                
    return f"Failed to connect to Gemini REST API: {last_error}"

async def check_model_status() -> Dict[str, Any]:
    """Verify if Gemini is accessible via direct REST API."""
    status = {
        "provider": "Google Gemini",
        "model": "gemini-2.0-flash-lite",
        "reachable": False,
        "error": None
    }
    
    if not settings.GEMINI_API_KEY:
        status["error"] = "Gemini API Key is missing"
        return status

    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": "ping"}]}]}
            
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                status["reachable"] = True
            else:
                # Try fallback for status check
                url_fallback = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                response_fb = await client.post(url_fallback, json=payload)
                if response_fb.status_code == 200:
                    status["reachable"] = True
                    status["model"] = "gemini-1.5-flash (fallback)"
                else:
                    status["error"] = f"REST Error: {response.status_code} - {response.text}"
        except Exception as e:
            status["error"] = f"Connection Exception: {str(e)}"
            
    return status

# ─── RAG & Vector Search ───────────────────────────────────────────────────

def get_embeddings(text: str) -> np.ndarray:
    model = get_embedding_model()
    if not model:
        return np.zeros((1, 384))
    return model.encode([text])

async def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieve relevant context from the FAISS index with stability checks."""
    try:
        index_path = f"{settings.FAISS_INDEX_PATH}.index"
        if not os.path.exists(index_path):
            return ""

        query_vector = await get_embeddings(query)
        index = faiss.read_index(index_path)
        
        # Stability check: Gemini uses 768-dim vectors. 
        # If the index is old (e.g., 384-dim), avoid a crash.
        if index.d != query_vector.shape[1]:
            print(f"Index dimension mismatch: expected {query_vector.shape[1]}, got {index.d}")
            return ""

        distances, indices = index.search(query_vector.astype('float32'), top_k)
        
        # Look up text for these indices in MongoDB
        db = get_database()
        cursor = db["ncert_chunks"].find({"index": {"$in": indices[0].tolist()}})
        chunks = await cursor.to_list(length=top_k)
        
        context_text = "\n\n".join([f"[Source: {c.get('source', 'NCERT')}] {c['text']}" for c in chunks])
        return context_text
    except Exception as e:
        print(f"RAG Retrieval Error: {e}")
        return ""

async def get_ai_explanation(question_text: str, student_answer: str, correct_answer: str, user_profile: Optional[Dict[str, Any]] = None) -> str:
    """Explains an MCQ question using context from NCERT."""
    # RAG: Retrieve context from NCERT
    context = await retrieve_context(question_text)
    
    selected_exam = user_profile.get("selected_exam", "NEET/JEE") if user_profile else "NEET/JEE"
    
    system_prompt = (
        f"You are an expert tutor for Indian competitive exams ({selected_exam}). "
        "Ground your answer in NCERT concepts. "
        "Explain step-by-step why the correct answer is right and why the student's choice might be wrong."
    )
    
    if context:
        system_prompt += f"\n\nUse the following reference material from NCERT:\n{context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Question: '{question_text}'\nStudent Answer: '{student_answer}'\nCorrect Answer: '{correct_answer}'"}
    ]
    
    return await chat_with_ai(messages)

async def chat_with_ai(messages: List[Dict[str, str]]) -> str:
    """General purpose chat with Google Gemini."""
    return await call_gemini(messages)

async def generate_mcqs(topic: str, subject: str, count: int = 5, difficulty: int = 3, exam_type: str = "NEET") -> List[Dict[str, Any]]:
    """Generates MCQs using Google Gemini."""
    # PRD §C.3 Difficulty Control Levers
    levers = {
        1: {"demand": "Direct recall", "scope": "Strictly in-text", "distractors": "Obviously wrong"},
        2: {"demand": "Single-step application", "scope": "In-text + exercises", "distractors": "Close but conceptually distinct"},
        3: {"demand": "Two-step reasoning", "scope": "Exercises + exemplar", "distractors": "Common formula errors"},
        4: {"demand": "Multi-step derivation", "scope": "Exemplar + extension", "distractors": "Subtle sign/unit errors"},
        5: {"demand": "Novel application + synthesis", "scope": "JEE Advanced scope", "distractors": "Indistinguishable without deep understanding"}
    }
    lever = levers.get(difficulty, levers[3])

    system_prompt = (
        f"You are an expert exam paper setter for Indian competitive exams ({exam_type}). "
        f"Generate {count} high-quality MCQs for the subject '{subject}' on the topic '{topic}'.\n"
        f"DIFFICULTY LEVEL {difficulty}:\n"
        f"- Cognitive Demand: {lever['demand']}\n"
        f"- Syllabus Scope: {lever['scope']}\n"
        f"- Distractor Strategy: {lever['distractors']}\n"
        "Return the response ONLY as a JSON array of objects. "
        "Each object must have: 'subject', 'topic', 'question_text', 'options' (list of 4 strings), "
        "'correct_option_index' (0-3), 'explanation', and 'difficulty'."
    )
    
    user_prompt = f"Generate {count} MCQs with depth suited for difficulty {difficulty}."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    response_text = await call_gemini(messages)
        
    if "Failed to connect" in response_text or "Error from" in response_text:
        print(f"CRITICAL: AI Error: {response_text}")
        return []
    
    try:
        # Extract JSON if the model wrapped it in code blocks or text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            cleaned = response_text.split("```")[1]
            if "\n" in cleaned:
                cleaned = "\n".join(cleaned.split("\n")[1:]) if cleaned.startswith("json") else cleaned
            response_text = cleaned.split("```")[0]
        
        # Clean up any potential markdown leftovers
        response_text = response_text.strip()
        
        # Final JSON load
        questions = json.loads(response_text)
        return questions
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return []
from datetime import datetime
from bson import ObjectId

async def create_chat_session(user_id: str, title: str = "New Chat") -> str:
    db = get_database()
    session = {
        "user_id": user_id,
        "title": title,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = await db["chat_sessions"].insert_one(session)
    return str(result.inserted_id)

async def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    db = get_database()
    cursor = db["chat_sessions"].find({"user_id": user_id}).sort("updated_at", -1)
    sessions = await cursor.to_list(length=100)
    for s in sessions:
        s["_id"] = str(s["_id"])
    return sessions

async def get_session_history(session_id: str, user_id: str) -> List[Dict[str, Any]]:
    db = get_database()
    # Verify session ownership
    session = await db["chat_sessions"].find_one({"_id": ObjectId(session_id), "user_id": user_id})
    if not session:
        return []
        
    history = await db["chat_history"].find_one({"session_id": session_id})
    if history:
        return history["messages"]
    return []

async def save_chat_message(session_id: str, user_id: str, message: Dict[str, str]):
    db = get_database()
    # Verify session ownership first
    session = await db["chat_sessions"].find_one({"_id": ObjectId(session_id), "user_id": user_id})
    if not session:
        return
        
    # Update or create chat history for this session
    await db["chat_history"].update_one(
        {"session_id": session_id},
        {"$push": {"messages": message}, "$set": {"updated_at": datetime.utcnow()}},
        upsert=True
    )
    # Also update session's updated_at
    await db["chat_sessions"].update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"updated_at": datetime.utcnow()}}
    )
