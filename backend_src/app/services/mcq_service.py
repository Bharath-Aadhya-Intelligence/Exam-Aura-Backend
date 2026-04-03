from typing import List
from datetime import datetime
from ..models.schemas import MCQQuestion
from ..db.mongodb import get_database
from .ai_service import generate_mcqs
from bson import ObjectId

async def get_daily_questions(user_id: str, category: str = None, count: int = 20) -> List[MCQQuestion]:
    db = get_database()
    
    try:
        # Try to get existing questions from DB
        query = {}
        if category:
            query["subject"] = category
            
        cursor = db["questions"].find(query).limit(count)
        questions = await cursor.to_list(length=count)
        
        if not questions:
            # If DB is empty, try to generate via AI
            try:
                user = await db["users"].find_one({"_id": ObjectId(user_id)})
            except Exception:
                user = None # Handle invalid ObjectId or strings
                
            user_profile = user.get("profile", {}) if user else {}
            exam_type = user_profile.get("selected_exam", "NEET")
            subject = category if category else ("Biology" if exam_type == "NEET" else "Physics")
            topic = "General"
            
            # Map confidence_level to difficulty
            difficulty = 3
            conf = user_profile.get("confidence_level", 50)
            if isinstance(conf, (int, float)):
                if conf < 1: conf *= 100 
                if conf <= 20: difficulty = 1
                elif conf <= 40: difficulty = 2
                elif conf <= 60: difficulty = 3
                elif conf <= 80: difficulty = 4
                else: difficulty = 5
            
            try:
                # Limit AI generation to a smaller count (e.g., 5) to avoid timeouts
                # Real users should have ingested data for large counts
                ai_count = min(count, 5)
                generated = await generate_mcqs(
                    topic=topic, 
                    subject=subject, 
                    count=ai_count, 
                    difficulty=difficulty,
                    exam_type=exam_type
                )
                
                if generated:
                    for q in generated:
                        q["_id"] = ObjectId()
                        await db["questions"].insert_one(q)
                    questions = generated
            except Exception as e:
                print(f"AI Generation Error: {e}")
                questions = []

        # Fallback to hardcoded sample questions if everything fails
        if not questions:
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
        
        # Format for Pydantic
        formatted_questions = []
        for q in questions:
            q["id"] = str(q.get("_id", ObjectId()))
            if "_id" in q: del q["_id"]
            formatted_questions.append(MCQQuestion(**q))
            
        return formatted_questions
    except Exception as e:
        print(f"MCQ Fetch Error: {e}")
        # Return hardcoded fallback instead of 500 error
        return [
            MCQQuestion(
                id=str(ObjectId()),
                subject="General",
                topic="System",
                question_text="Could not load your questions. Please check back later.",
                options=["Acknowledged", "Retry", "Wait", "See Results"],
                correct_option_index=0,
                explanation="System Error occurred during fetch."
            )
        ]

async def submit_session(user_id: str, question_ids: List[str], answers: List[int]):
    db = get_database()
    
    # Calculate score, subject breakdown, and topic breakdown
    score = 0
    subject_stats = {}
    topic_stats = {}
    
    for q_id, ans in zip(question_ids, answers):
        q = await db["questions"].find_one({"_id": ObjectId(q_id)})
        if q:
            subj = q.get("subject", "General")
            topic = q.get("topic", "General")
            
            # Subject stats
            if subj not in subject_stats:
                subject_stats[subj] = {"correct": 0, "total": 0}
            subject_stats[subj]["total"] += 1
            
            # Topic stats
            if topic not in topic_stats:
                topic_stats[topic] = {"correct": 0, "total": 0}
            topic_stats[topic]["total"] += 1
            
            if q["correct_option_index"] == ans:
                score += 1
                subject_stats[subj]["correct"] += 1
                topic_stats[topic]["correct"] += 1
    
    session = {
        "user_id": user_id,
        "score": score,
        "total": len(question_ids),
        "subject_breakdown": subject_stats,
        "topic_breakdown": topic_stats,
        "timestamp": datetime.utcnow()
    }
    await db["sessions"].insert_one(session)
    return {
        "score": score, 
        "total": len(question_ids), 
        "breakdown": subject_stats,
        "topic_breakdown": topic_stats
    }
