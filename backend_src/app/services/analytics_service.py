from typing import Dict, Any, List, Optional
from ..db.mongodb import get_database
from bson import ObjectId
from datetime import datetime, timedelta
import json
import asyncio
from .ai_service import call_gemini, call_groq
from ..models.schemas import AnalyticsDetailedResponse

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

async def get_detailed_analytics(user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Hybrid AI Analytics Engine with Caching and Performance Trending.
    """
    db = get_database()
    
    # Get last session to build cache key
    last_session = await db["sessions"].find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    last_session_time = last_session["timestamp"] if last_session else datetime.min
    
    # 1. Check Cache
    if not force_refresh:
        cached = await db["analytics_cache"].find_one({"user_id": user_id})
        if cached:
            # Re-generate if cache is older than 1 hour or user has new activity
            cache_age = datetime.utcnow() - cached["created_at"]
            if cache_age < timedelta(hours=1) and cached["last_session_time"] == last_session_time:
                return cached["data"]

    # 2. Gather Real-Time Specs
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)
    
    # Fetch Today's Stats
    today_cursor = db["sessions"].find({
        "user_id": user_id,
        "timestamp": {"$gte": today_start}
    })
    today_sessions = await today_cursor.to_list(length=100)
    
    # Fetch Yesterday's Stats
    yesterday_cursor = db["sessions"].find({
        "user_id": user_id,
        "timestamp": {"$gte": yesterday_start, "$lt": today_start}
    })
    yesterday_sessions = await yesterday_cursor.to_list(length=100)
    
    # Aggregation
    def aggregate_stats(sessions):
        total = sum(s.get("total", 0) for s in sessions)
        correct = sum(s.get("score", 0) for s in sessions)
        topics = {}
        for s in sessions:
            topic_stats = s.get("topic_breakdown", s.get("subject_breakdown", {}))
            for topic, data in topic_stats.items():
                if topic not in topics:
                    topics[topic] = {"correct": 0, "incorrect": 0, "total": 0}
                topics[topic]["total"] += data["total"]
                topics[topic]["correct"] += data["correct"]
                topics[topic]["incorrect"] += (data["total"] - data["correct"])
        
        accuracy = (correct / total * 100) if total > 0 else 0
        return total, correct, accuracy, topics

    t_total, t_correct, t_acc, t_topics = aggregate_stats(today_sessions)
    y_total, y_correct, y_acc, _ = aggregate_stats(yesterday_sessions)
    
    # Prepare Topic List for AI (limit to top 5 for brevity)
    ai_topics = [
        {"topic": name, "correct": data["correct"], "incorrect": data["incorrect"], "avg_time": 45}
        for name, data in list(t_topics.items())[:5]
    ] if t_topics else []

    # 3. Call AI Analytics Engine
    ai_prompt = f"""
    date: {now.strftime("%Y-%m-%d")}
    questions_attempted: {t_total}
    correct_answers: {t_correct}
    incorrect_answers: {t_total - t_correct}
    topics: {json.dumps(ai_topics)}
    total_time_spent: {t_total * 0.75}
    previous_accuracy: {y_acc if y_total > 0 else 0}
    previous_growth: {t_acc - y_acc if y_total > 0 else 0}
    no_data_yesterday: {True if y_total == 0 else False}
    """
    
    system_instruction = """
    You are a real-time analytics engine for ExamAura.
    Process the student data and return ONLY valid JSON.
    If 'no_data_yesterday' is true, mention "No data for yesterday" in insights.
    
    Format:
    {
      "activity": {"date": "YYYY-MM-DD", "activity_level": "none|low|medium|high", "questions_attempted": number},
      "performance": {"accuracy": number, "total_solved": number, "efficiency": "low|medium|high", "growth": number},
      "trend": {"status": "improving|declining|stable", "change": number},
      "weak_topics": [{"topic": "string", "accuracy": number, "issue": "conceptual|time|careless"}],
      "insights": ["string", "string"],
      "recommendation": {"focus_topic": "string", "action": "string"}
    }
    Rules: Round numbers, keep insights < 12 words, return ONLY JSON.
    """
    
    try:
        # Try Gemini first, fallback to Groq
        ai_response = await call_gemini([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": ai_prompt}
        ])
        
        # Clean potential markdown
        if "```" in ai_response:
            ai_response = ai_response.split("```json")[-1].split("```")[0].strip()
        
        analytics_data = json.loads(ai_response)
    except Exception as e:
        # Emergency Fallback JSON if AI is down
        analytics_data = {
            "activity": {"date": now.strftime("%Y-%m-%d"), "activity_level": "low" if t_total > 0 else "none", "questions_attempted": t_total},
            "performance": {"accuracy": round(t_acc, 2), "total_solved": t_total, "efficiency": "medium", "growth": 0},
            "trend": {"status": "stable", "change": 0},
            "weak_topics": [],
            "insights": ["Connectivity issue with analytics engine.", "Using raw calculation fallback."],
            "recommendation": {"focus_topic": "General", "action": "Keep practicing to generate insights."}
        }

    # 4. Save to Cache
    cache_entry = {
        "user_id": user_id,
        "last_session_time": last_session_time,
        "data": analytics_data,
        "created_at": datetime.utcnow()
    }
    await db["analytics_cache"].update_one(
        {"user_id": user_id},
        {"$set": cache_entry},
        upsert=True
    )
    
    return analytics_data
