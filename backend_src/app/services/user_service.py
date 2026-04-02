from datetime import datetime
import base64
from bson import ObjectId
from fastapi import UploadFile
from ..db.mongodb import get_database
from ..models.schemas import UserCreate, UserInDB
from ..core.security import get_password_hash

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
    user_in_db["id"] = str(result.inserted_id)
    return user_in_db

async def get_user_by_email(email: str):
    db = get_database()
    user = await db["users"].find_one({"email": email})
    if user:
        user["id"] = str(user["_id"])
    return user

async def update_user_profile(email: str, profile_data: dict):
    db = get_database()
    result = await db["users"].update_one(
        {"email": email},
        {"$set": {"profile": profile_data}}
    )
    return result.modified_count > 0

async def update_profile_photo(email: str, file: UploadFile):
    db = get_database()
    content = await file.read()
    # Check file size (e.g., max 2MB)
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("File too large (max 2MB)")
    
    # Check file type
    if not file.content_type.startswith("image/"):
        raise ValueError("File must be an image")

    encoded_string = base64.b64encode(content).decode("utf-8")
    data_uri = f"data:{file.content_type};base64,{encoded_string}"
    
    result = await db["users"].update_one(
        {"email": email},
        {"$set": {"profile_photo": data_uri}}
    )
    return result.modified_count > 0

async def update_user(email: str, update_data: dict):
    db = get_database()
    result = await db["users"].update_one(
        {"email": email},
        {"$set": update_data}
    )
    return result.modified_count > 0
