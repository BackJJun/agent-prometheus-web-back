from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import fetch_database_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/health/db")
async def database_health_check() -> dict[str, object]:
    try:
        return await fetch_database_health()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database health check failed") from exc
