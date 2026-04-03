from fastapi import APIRouter, Depends
from ....models.schemas import UserPublic
from ....core.deps import get_current_user
from ....services import analytics_service

router = APIRouter()

@router.get("/performance")
async def get_performance(current_user: UserPublic = Depends(get_current_user)):
    return await analytics_service.get_user_performance(current_user.id)
