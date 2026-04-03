import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "exam_aura")

SAMPLE_QUESTIONS = [
    {
        "subject": "Physics",
        "topic": "Newton's Laws",
        "question_text": "A body of mass 2kg is acted upon by a force of 10N. What is the acceleration?",
        "options": ["2 m/s²", "5 m/s²", "20 m/s²", "0.2 m/s²"],
        "correct_option_index": 1,
        "explanation": "Using F = ma, a = F/m = 10N / 2kg = 5 m/s²."
    },
    {
        "subject": "Chemistry",
        "topic": "Chemical Bonding",
        "question_text": "Which of the following molecules has a triple bond?",
        "options": ["O₂", "N₂", "H₂", "Cl₂"],
        "correct_option_index": 1,
        "explanation": "Nitrogen (N₂) has a triple covalent bond between its atoms."
    },
    {
        "subject": "Biology",
        "topic": "Cell Biology",
        "question_text": "Which organelle is known as the powerhouse of the cell?",
        "options": ["Nucleus", "Ribosome", "Mitochondria", "Golgi apparatus"],
        "correct_option_index": 2,
        "explanation": "Mitochondria are responsible for ATP production, hence the name powerhouse."
    }
]

async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    # Check if empty
    count = await db["questions"].count_documents({})
    if count == 0:
        print(f"Seeding {len(SAMPLE_QUESTIONS)} questions...")
        await db["questions"].insert_many(SAMPLE_QUESTIONS)
        print("Seeding completed.")
    else:
        print(f"Database already contains {count} questions. Skipping seed.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
