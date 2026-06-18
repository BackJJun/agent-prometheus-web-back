from datetime import datetime

from pydantic import BaseModel


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
