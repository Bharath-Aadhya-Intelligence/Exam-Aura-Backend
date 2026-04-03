from typing import List
from datetime import datetime
from ..models.schemas import MCQQuestion
from ..db.mongodb import get_database
from .ai_service import generate_mcqs
from bson import ObjectId

async def get_daily_questions(user_id: str, count: int = 5) -> List[MCQQuestion]:
    db = get_database()
    
    # Try to get questions from DB
    cursor = db["questions"].find().limit(count)
    questions = await cursor.to_list(length=count)
    
    if not questions:
        # If DB is empty, try to generate via AI
        # We fetch user's profile to get context
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        user_profile = user.get("profile", {}) if user else {}
        exam_type = user_profile.get("selected_exam", "NEET")
        subject = "Biology" if exam_type == "NEET" else "Physics"
        topic = "General"
        
        # Map confidence_level (0-100 from frontend) to difficulty (1-5)
        difficulty = 3
        conf = user_profile.get("confidence_level", 50)
        # Standardize conf to 0-100 range
        if isinstance(conf, (int, float)):
            if conf < 1: conf *= 100 
            
            if conf <= 20: difficulty = 1
            elif conf <= 40: difficulty = 2
            elif conf <= 60: difficulty = 3
            elif conf <= 80: difficulty = 4
            else: difficulty = 5
        
        generated = await generate_mcqs(
            topic=topic, 
            subject=subject, 
            count=count, 
            difficulty=difficulty,
            exam_type=exam_type
        )
        
        if generated:
            # Save to DB for future use
            for q in generated:
                q["_id"] = ObjectId()
                await db["questions"].insert_one(q)
            questions = generated
        else:
            # Fallback to hardcoded sample questions if AI fails
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
    
    # Calculate score and subject breakdown
    score = 0
    subject_stats = {}
    
    for q_id, ans in zip(question_ids, answers):
        q = await db["questions"].find_one({"_id": ObjectId(q_id)})
        if q:
            subj = q.get("subject", "General")
            if subj not in subject_stats:
                subject_stats[subj] = {"correct": 0, "total": 0}
            
            subject_stats[subj]["total"] += 1
            if q["correct_option_index"] == ans:
                score += 1
                subject_stats[subj]["correct"] += 1
    
    session = {
        "user_id": user_id,
        "score": score,
        "total": len(question_ids),
        "subject_breakdown": subject_stats,
        "timestamp": datetime.utcnow()
    }
    await db["sessions"].insert_one(session)
    return {"score": score, "total": len(question_ids), "breakdown": subject_stats}
