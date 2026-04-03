from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import get_settings

settings = get_settings()
client = AsyncIOMotorClient(settings.MONGODB_URL)

def get_database():
    return client[settings.DATABASE_NAME]

async def ping_database() -> bool:
    """Check if MongoDB is reachable."""
    try:
        # The ping command is cheap and does not require auth for reachability check
        await client.admin.command('ping')
        return True
    except Exception as e:
        print(f"MongoDB Ping Error: {e}")
        return False
