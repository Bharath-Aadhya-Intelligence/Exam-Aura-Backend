import asyncio
import httpx
import sys
import os

# Add the parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongodb import ping_database
from app.services.ai_service import check_model_status
from app.core.config import get_settings

async def main():
    settings = get_settings()
    print("=== PrepAI Connectivity Check ===")
    print(f"Checking MongoDB at: {settings.MONGODB_URL}")
    
    db_alive = await ping_database()
    if db_alive:
        print("[OK] MongoDB is connected.")
    else:
        print("[ERROR] MongoDB is NOT reachable. Ensure your local MongoDB or Atlas link is correct in .env.")

    print("\nChecking AI Model status (Google Gemini)")
    ai_status = await check_model_status()
    
    if ai_status["reachable"]:
        print(f"[OK] AI Model '{ai_status['model']}' is reachable.")
    else:
        print(f"[ERROR] AI Model is NOT ready: {ai_status['error']}")
        print("TIP: Ensure your GEMINI_API_KEY is correct in .env.")

    print("\n=== Check Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
