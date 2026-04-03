from typing import List, Dict, Any
import httpx
from .ai_service import retrieve_context, chat_with_ai
from ..core.config import get_settings

settings = get_settings()

async def query_classifier(query: str) -> str:
    """Classify query for routing: factual/conceptual vs computation."""
    prompt = (
        f"Classify the following query for an exam prep tutor: '{query}'\n"
        "Categories: 'conceptual' (needs RAG), 'factual' (needs RAG), 'calculation' (direct LLM).\n"
        "Return ONLY the category name."
    )
    messages = [{"role": "user", "content": prompt}]
    return await chat_with_ai(messages)

async def grounded_chat(query: str, user_level: str = "beginner") -> Dict[str, Any]:
    """Retrieve context and generate grounded response with confidence score."""
    
    # 1. Classify
    category = await query_classifier(query)
    
    # 2. Retrieve (if needed)
    context = ""
    if category.strip().lower() in ["conceptual", "factual"]:
        context = await retrieve_context(query)
        
    # 3. Assemble Prompt
    system_prompt = (
        f"You are a patient, expert tutor for Indian competitive exams. "
        f"Answer using ONLY the reference material provided. "
        f"If the answer is not in the material, say 'I need more context'. "
        f"Student level: {user_level}."
    )
    
    if context:
        system_prompt += f"\n\nREFERENCE MATERIAL:\n{context}"
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    # 4. Generate & Score
    answer = await chat_with_ai(messages)
    
    # Mock confidence score (§A.2.6)
    confidence = 0.95 if context else 0.50
    
    return {
        "answer": answer,
        "context_retrieved": bool(context),
        "confidence_score": confidence,
        "category": category
    }
