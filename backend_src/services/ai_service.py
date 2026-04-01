import httpx
from ..config import get_settings

settings = get_settings()

async def get_ai_explanation(question_text: str, student_answer: str, correct_answer: str) -> str:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-api-key":
        return "AI Explanation is unavailable. Please provide a valid Groq API Key."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192", # Using a common Groq model
        "messages": [
            {"role": "system", "content": "You are an expert tutor for NEET/JEE exams. Explain concepts clearly and concisely."},
            {"role": "user", "content": f"The student chose '{student_answer}' for the question: '{question_text}'. The correct answer is '{correct_answer}'. Explain why the correct answer is right and why the student's choice might be wrong."}
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Error from AI service: {response.text}"
        except Exception as e:
            return f"Failed to connect to AI service: {str(e)}"
