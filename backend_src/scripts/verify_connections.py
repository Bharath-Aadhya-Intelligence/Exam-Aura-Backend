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

    print(f"\nChecking AI Model status (Local: {settings.USE_LOCAL_MODEL})")
    ai_status = await check_model_status()
    
    if ai_status["reachable"]:
        print(f"[OK] AI Model '{ai_status['model']}' is reachable via {ai_status['provider']}.")
    else:
        print(f"[ERROR] AI Model is NOT ready: {ai_status['error']}")
        if settings.USE_LOCAL_MODEL and "not found" in ai_status["error"].lower():
            print(f"TIP: Run 'ollama pull {settings.LOCAL_MODEL_NAME}' to download the model.")
        elif settings.USE_LOCAL_MODEL:
             print("TIP: Ensure Ollama is running on your machine.")

    print("\n=== Check Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
