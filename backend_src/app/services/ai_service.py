import httpx
from typing import List, Dict
from ..core.config import get_settings

settings = get_settings()

async def get_ai_explanation(
    question_text: str, 
    student_answer: str, 
    correct_answer: str,
    history: List[Dict[str, str]] = None
) -> str:
    """Explains an MCQ question answer logic, optionally with history."""
    if not settings.OPENAI_API_KEY:
        return "AI Error: OpenAI API Key is missing. Please add it to your .env file."

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"Question: '{question_text}'\n"
        f"Correct Answer: '{correct_answer}'\n"
        f"Student's Answer: '{student_answer}'\n\n"
        "Please explain why the correct answer is true and help the student understand any misconception."
    )

    messages = [
        {
            "role": "system", 
            "content": "You are an expert tutor for NEET/JEE exams. Explain concepts clearly and concisely with encouraging tone."
        }
    ]
    
    if history:
        messages.extend(history)
    
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.5
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Error from AI service (HTTP {response.status_code}): {response.text}"
        except Exception as e:
            return f"Failed to connect to OpenAI: {str(e)}"

async def get_chatbot_response(messages: List[Dict[str, str]]) -> str:
    """General purpose chatbot with history."""
    if not settings.OPENAI_API_KEY:
        return "Chat Error: OpenAI API Key is missing. Please add it to your .env file."

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Prepend dynamic system message
    full_messages = [
        {
            "role": "system", 
            "content": (
                "You are Exam Aura, a premium AI tutor for competitive exams (NEET/JEE/CET). "
                "Be supportive, professional, and clear. Use Bullet points for readability. "
                "Format mathematical and chemical expressions using LaTeX-like notation (e.g., $H_2O$, $x^2$). "
                "If asked about progress or strategy, provide actionable study tips."
            )
        },
        *messages
    ]

    payload = {
        "model": "gpt-4o-mini",
        "messages": full_messages,
        "temperature": 0.7
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=45.0)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"AI Error ({response.status_code}): {response.text}"
        except Exception as e:
            return f"Chat Error: {str(e)}"
