from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.plugin_history import (
    PluginEventListResponse,
    PluginFileListResponse,
    PluginHistoryDetail,
    PluginHistoryListResponse,
    PluginMessageListResponse,
)
from app.services.plugin_history_service import (
    get_plugin_history,
    list_plugin_events,
    list_plugin_files,
    list_plugin_histories,
    list_plugin_messages,
)

router = APIRouter(prefix="/api/plugin-histories", tags=["plugin histories"])


@router.get("", response_model=PluginHistoryListResponse)
async def get_histories(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_plugin_histories()}


@router.get("/{task_id}", response_model=PluginHistoryDetail)
async def get_history(
    task_id: str, _current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, object]:
    history = await get_plugin_history(task_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Plugin history not found")
    return history


@router.get("/{task_id}/messages", response_model=PluginMessageListResponse)
async def get_messages(
    task_id: str, _current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, object]:
    messages = await list_plugin_messages(task_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Plugin history not found")
    return {"items": messages}


@router.get("/{task_id}/events", response_model=PluginEventListResponse)
async def get_events(
    task_id: str, _current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, object]:
    events = await list_plugin_events(task_id)
    if events is None:
        raise HTTPException(status_code=404, detail="Plugin history not found")
    return {"items": events}


@router.get("/{task_id}/files", response_model=PluginFileListResponse)
async def get_files(
    task_id: str, _current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, object]:
    files = await list_plugin_files(task_id)
    if files is None:
        raise HTTPException(status_code=404, detail="Plugin history not found")
    return {"items": files}
