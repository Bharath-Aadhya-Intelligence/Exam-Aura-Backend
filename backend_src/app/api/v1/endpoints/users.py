from fastapi import APIRouter, Depends, HTTPException
from ....models.schemas import UserPublic, OnboardingData
from ....core.deps import get_current_user
from ....db.mongodb import get_database

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user

@router.post("/onboarding")
async def update_onboarding(
    data: OnboardingData, 
    current_user: UserPublic = Depends(get_current_user)
):
    db = get_database()
    # Convert data to dict, ensuring datetime is handled (FastAPI does this usually)
    profile_dict = data.dict()
    
    result = await db["users"].update_one(
        {"email": current_user.email},
        {"$set": {"profile": profile_dict}}
    )
    
    if result.modified_count == 0:
        # Check if it was because it already exists or what
        # In most cases, if values are identical it returns 0.
        pass
        
    return {"message": "Onboarding data updated successfully"}
