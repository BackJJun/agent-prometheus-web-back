from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageListResponse,
    ChatSessionCreateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.chat_service import (
    archive_chat_session,
    create_chat_message,
    create_chat_session,
    get_chat_session,
    list_chat_messages,
    list_chat_sessions,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _user_id(current_user: dict[str, Any]) -> str:
    return str(current_user["id"])


@router.get("/sessions", response_model=ChatSessionListResponse)
async def get_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_chat_sessions(_user_id(current_user))}


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def post_session(
    request: ChatSessionCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return await create_chat_session(_user_id(current_user), request.title, request.mode)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    session = await get_chat_session(_user_id(current_user), session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.post("/sessions/{session_id}/archive", response_model=ChatSessionResponse)
async def post_archive_session(
    session_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    session = await archive_chat_session(_user_id(current_user), session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
async def get_messages(
    session_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    messages = await list_chat_messages(_user_id(current_user), session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"items": messages}


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    session_id: UUID,
    request: ChatMessageCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    result = await create_chat_message(_user_id(current_user), session_id, request.content)
    if result is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return result
