from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.monitoring import BridgeStatusResponse, MonitoringEventListResponse, ServiceHealthCheckListResponse
from app.services.bridge_status_service import fetch_bridge_status
from app.services.monitoring_service import list_monitoring_events, list_service_health_checks

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/events", response_model=MonitoringEventListResponse)
async def get_events(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_monitoring_events()}


@router.get("/health-checks", response_model=ServiceHealthCheckListResponse)
async def get_health_checks(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_service_health_checks()}


@router.get("/bridge/status", response_model=BridgeStatusResponse)
async def get_bridge_status(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return await fetch_bridge_status()

