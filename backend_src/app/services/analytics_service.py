from typing import Dict, Any, List
from ..db.mongodb import get_database
from bson import ObjectId

async def get_user_performance(user_id: str) -> Dict[str, Any]:
    db = get_database()
    
    # Query sessions for this user, sorted by time
    cursor = db["sessions"].find({"user_id": user_id}).sort("timestamp", 1)
    sessions = await cursor.to_list(length=100)
    
    total_sessions = len(sessions)
    if total_sessions == 0:
        return {
            "total_questions": 0,
            "correct_answers": 0,
            "accuracy": 0,
            "recent_scores": [],
            "subject_breakdown": {},
            "streak": 0
        }
    
    total_questions = sum(s.get("total", 0) for s in sessions)
    correct_answers = sum(s.get("score", 0) for s in sessions)
    accuracy = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Real Subject breakdown aggregation
    subject_breakdown = {}
    for session in sessions:
        breakdown = session.get("subject_breakdown", {})
        for subject, stats in breakdown.items():
            if subject not in subject_breakdown:
                subject_breakdown[subject] = {"correct": 0, "total": 0}
            subject_breakdown[subject]["correct"] += stats["correct"]
            subject_breakdown[subject]["total"] += stats["total"]
    
    # Last 5 scores for the trend chart
    recent_scores = [
        {"score": s["score"], "total": s["total"], "timestamp": s["timestamp"]}
        for s in sessions[-5:]
    ]
    
    # Simple Streak logic (days with sessions)
    streak = 0
    if sessions:
        # Sort and get unique days
        days = sorted(list(set(s["timestamp"].date() for s in sessions)), reverse=True)
        # Check consecutive days from today/most recent
        for i in range(len(days)):
            if i == 0 or (days[i-1] - days[i]).days == 1:
                streak += 1
            else:
                break

    return {
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "accuracy": round(accuracy, 2),
        "recent_scores": recent_scores,
        "total_sessions": total_sessions,
        "subject_breakdown": subject_breakdown,
        "streak": streak
    }
