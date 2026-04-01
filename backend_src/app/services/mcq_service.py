from typing import List
from datetime import datetime
from ..models.schemas import MCQQuestion
from ..db.mongodb import get_database
from bson import ObjectId

async def get_daily_questions(user_id: str, count: int = 5) -> List[MCQQuestion]:
    db = get_database()
    # For now, return sample questions if DB is empty
    cursor = db["questions"].find().limit(count)
    questions = await cursor.to_list(length=count)
    
    if not questions:
        # Sample questions for initial testing
        questions = [
            {
                "_id": ObjectId(),
                "subject": "Physics",
                "topic": "Newton's Laws",
                "question_text": "What is the unit of force?",
                "options": ["Newton", "Joule", "Watt", "Pascal"],
                "correct_option_index": 0,
                "explanation": "The SI unit of force is the Newton (N)."
            },
            {
                "_id": ObjectId(),
                "subject": "Chemistry",
                "topic": "Atomic Structure",
                "question_text": "Which particle has a positive charge?",
                "options": ["Electron", "Neutron", "Proton", "Photon"],
                "correct_option_index": 2,
                "explanation": "Protons have a positive charge of +1e."
            }
        ]
    
    for q in questions:
        q["id"] = str(q["_id"])
    return [MCQQuestion(**q) for q in questions]

async def submit_session(user_id: str, question_ids: List[str], answers: List[int]):
    db = get_database()
    # Calculate score (simplified logic)
    score = 0
    detailed_results = []
    for q_id, ans in zip(question_ids, answers):
        q = await db["questions"].find_one({"_id": ObjectId(q_id)})
        if q and q["correct_option_index"] == ans:
            score += 1
    
    session = {
        "user_id": user_id,
        "score": score,
        "total": len(question_ids),
        "timestamp": datetime.utcnow()
    }
    await db["sessions"].insert_one(session)
    return {"score": score, "total": len(question_ids)}
