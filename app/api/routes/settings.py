from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.settings import (
    LlmModelListResponse,
    LlmProviderListResponse,
    NotificationSettingListResponse,
)
from app.services.settings_service import (
    list_llm_models,
    list_llm_providers,
    list_notification_settings,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/llm-providers", response_model=LlmProviderListResponse)
async def get_llm_providers(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_llm_providers()}


@router.get("/llm-models", response_model=LlmModelListResponse)
async def get_llm_models(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_llm_models()}


@router.get("/notification-settings", response_model=NotificationSettingListResponse)
async def get_notification_settings(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_notification_settings()}
