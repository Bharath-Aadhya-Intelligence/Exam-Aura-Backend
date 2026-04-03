from fastapi import APIRouter, Depends
from backend_src.app.models.schemas import UserPublic
from backend_src.app.core.deps import get_current_user
from backend_src.app.services import analytics_service

router = APIRouter()

@router.get("/performance")
async def get_performance(current_user: UserPublic = Depends(get_current_user)):
    return await analytics_service.get_user_performance(current_user.id)

@router.get("/detailed", response_model=AnalyticsDetailedResponse)
async def get_detailed_analytics(
    refresh: bool = False,
    current_user: UserPublic = Depends(get_current_user)
):
    return await analytics_service.get_detailed_analytics(current_user.id, force_refresh=refresh)
