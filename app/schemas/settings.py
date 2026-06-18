from datetime import datetime

from pydantic import BaseModel, Field


class LlmProviderCreateRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="active", pattern="^(active|inactive|error)$")


class LlmProviderResponse(BaseModel):
    id: str
    workspace_id: str
    provider: str
    base_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class LlmProviderListResponse(BaseModel):
    items: list[LlmProviderResponse]


class LlmModelCreateRequest(BaseModel):
    provider_id: str
    name: str = Field(min_length=1, max_length=120)
    model_key: str = Field(min_length=1, max_length=200)
    context_window: int | None = Field(default=None, ge=1)
    enabled: bool = True
    status: str = Field(default="active", pattern="^(active|inactive|deprecated)$")


class LlmModelResponse(BaseModel):
    id: str
    provider_id: str
    name: str
    model_key: str
    context_window: int | None
    enabled: bool
    status: str
    created_at: datetime
    updated_at: datetime


class LlmModelListResponse(BaseModel):
    items: list[LlmModelResponse]


class NotificationSettingResponse(BaseModel):
    id: str
    workspace_id: str
    channel: str
    enabled: bool
    target: str | None
    events: list[str]
    created_at: datetime
    updated_at: datetime


class NotificationSettingListResponse(BaseModel):
    items: list[NotificationSettingResponse]
