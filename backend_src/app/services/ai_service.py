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

settings = get_settings()

# Initialize Embedding Model (Lazy Loading)
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None and SentenceTransformer is not None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _embedding_model

# Groq support removed for Phi-3 Exclusive Production

async def call_ollama(messages: List[Dict[str, str]], model: str = None) -> str:
    if not model:
        model = settings.LOCAL_MODEL_NAME
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=120.0)
            if response.status_code == 200:
                data = response.json()
                return data["message"]["content"]
            return f"Error from Ollama: {response.text}"
        except Exception as e:
            return f"Failed to connect to Ollama: {str(e)}"

async def check_model_status() -> Dict[str, Any]:
    """Verify if the AI model (local/cloud) is currently accessible."""
    status = {
        "provider": "Local (Ollama)" if settings.USE_LOCAL_MODEL else "Cloud (Groq)",
        "model": settings.LOCAL_MODEL_NAME if settings.USE_LOCAL_MODEL else "llama3",
        "reachable": False,
        "error": None
    }
    
    if settings.USE_LOCAL_MODEL:
        url = f"{settings.OLLAMA_BASE_URL}/api/tags"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    # Check if our specified model is in the list
                    model_names = [m["name"] for m in models]
                    if settings.LOCAL_MODEL_NAME in model_names or any(settings.LOCAL_MODEL_NAME in m for m in model_names):
                        status["reachable"] = True
                    else:
                        status["error"] = f"Model '{settings.LOCAL_MODEL_NAME}' not found in Ollama. Available: {', '.join(model_names)}"
                else:
                    status["error"] = f"Ollama returned status {response.status_code}"
            except Exception as e:
                status["error"] = f"Could not connect to Ollama: {str(e)}"
    else:
        # Simple Groq reachability check (dummy)
        status["reachable"] = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your-groq-api-key")
        if not status["reachable"]:
            status["error"] = "Invalid or missing Groq API Key"
            
    return status

# ─── RAG & Vector Search ───────────────────────────────────────────────────

def get_embeddings(text: str) -> np.ndarray:
    model = get_embedding_model()
    if not model:
        return np.zeros((1, 384))
    return model.encode([text])

async def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieve relevant NCERT chunks from FAISS index and MongoDB."""
    if faiss is None:
        return ""
        
    index_path = f"{settings.FAISS_INDEX_PATH}.index"
    if not os.path.exists(index_path):
        return "" 
        
    try:
        index = faiss.read_index(index_path)
        query_vector = get_embeddings(query)
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
    """General purpose chat with Phi-3."""
    # Exclusive Phi-3 (Ollama) Implementation
    response = await call_ollama(messages)
    if "Failed to connect to Ollama" in response:
        return "AI service is currently offline. Please ensure Ollama is running locally with Phi-3."
    return response

async def generate_mcqs(topic: str, subject: str, count: int = 5, difficulty: int = 3, exam_type: str = "NEET") -> List[Dict[str, Any]]:
    """Generates MCQs using Phi-3."""
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
    
    response_text = await call_ollama(messages)
    if "Failed to connect to Ollama" in response_text:
        print("CRITICAL: Ollama is not responding.")
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
