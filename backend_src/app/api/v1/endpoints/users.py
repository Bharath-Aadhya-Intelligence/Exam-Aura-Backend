from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from ....models.schemas import UserPublic, OnboardingData
from ....core.deps import get_current_user
from ....services import user_service

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserPublic)
async def update_users_me(
    update_data: dict,
    current_user: UserPublic = Depends(get_current_user)
):
    success = await user_service.update_user(current_user.email, update_data)
    if not success:
        raise HTTPException(status_code=400, detail="Update failed or no changes made")
    
    # Return updated user
    updated_user = await user_service.get_user_by_email(current_user.email)
    return updated_user

@router.get("/profile", response_model=OnboardingData)
async def get_profile(current_user: UserPublic = Depends(get_current_user)):
    if not current_user.profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return current_user.profile

@router.post("/profile/photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user)
):
    try:
        success = await user_service.update_profile_photo(current_user.email, file)
        if not success:
            raise HTTPException(status_code=400, detail="Photo upload failed")
        return {"message": "Profile photo uploaded successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/onboarding")
async def update_onboarding(
    data: OnboardingData, 
    current_user: UserPublic = Depends(get_current_user)
):
    success = await user_service.update_user_profile(
        current_user.email, data.dict(exclude_unset=True)
    )
    
    if not success:
        # It might be because data is identical, but we treat it as success or return specific msg
        return {"message": "Profile already up to date or no changes made"}
        
    return {"message": "Onboarding data updated successfully"}
