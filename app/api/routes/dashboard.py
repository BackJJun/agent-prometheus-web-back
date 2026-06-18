from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_current_user
from app.schemas.common import CurrentUserResponse
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import fetch_dashboard_summary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    _current_user: CurrentUserResponse = Depends(get_current_user),
) -> dict[str, object]:
    try:
        return await fetch_dashboard_summary()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Dashboard summary query failed") from exc
