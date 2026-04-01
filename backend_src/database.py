from motor.motor_asyncio import AsyncIOMotorClient
from .config import get_settings

settings = get_settings()

client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

def get_database():
    return db
