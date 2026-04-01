from datetime import datetime
from bson import ObjectId
from ..database import get_database
from ..models import UserCreate, UserInDB
from ..auth import get_password_hash

async def create_user(user: UserCreate):
    db = get_database()
    hashed_password = get_password_hash(user.password)
    user_in_db = {
        "email": user.email,
        "name": user.name,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    result = await db["users"].insert_one(user_in_db)
    user_in_db["_id"] = str(result.inserted_id)
    return user_in_db

async def get_user_by_email(email: str):
    db = get_database()
    user = await db["users"].find_one({"email": email})
    if user:
        user["id"] = str(user["_id"])
    return user
