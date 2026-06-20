from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    mode: str = "chat"


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=200)


class ChatSessionResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    mode: str
    status: str
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    parent_message_id: str | None
    role: str
    content: str
    status: str
    token_count: int
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]


class ChatMessageCreateResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
