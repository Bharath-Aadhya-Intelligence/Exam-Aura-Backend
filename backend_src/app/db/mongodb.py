from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import get_settings

settings = get_settings()
client = AsyncIOMotorClient(settings.MONGODB_URL)

def get_database():
    return client[settings.DATABASE_NAME]
