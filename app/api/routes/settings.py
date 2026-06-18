from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.schemas.settings import (
    LlmModelCreateRequest,
    LlmModelListResponse,
    LlmModelResponse,
    LlmProviderCreateRequest,
    LlmProviderListResponse,
    LlmProviderResponse,
    NotificationSettingListResponse,
)
from app.services.settings_service import (
    create_llm_model,
    create_llm_provider,
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


@router.post(
    "/llm-providers",
    response_model=LlmProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_llm_provider(
    request: LlmProviderCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return await create_llm_provider(current_user["id"], request.model_dump())


@router.get("/llm-models", response_model=LlmModelListResponse)
async def get_llm_models(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_llm_models()}


@router.post(
    "/llm-models",
    response_model=LlmModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_llm_model(
    request: LlmModelCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    model = await create_llm_model(current_user["id"], request.model_dump())
    if model is None:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    return model


@router.get("/notification-settings", response_model=NotificationSettingListResponse)
async def get_notification_settings(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_notification_settings()}
