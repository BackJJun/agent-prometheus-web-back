from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PluginHistorySummary(BaseModel):
    id: str
    task_id: str
    source: str
    title: str
    task: str | None
    status: str
    mode: str | None
    workspace_path: str | None
    source_started_at: datetime | None
    source_updated_at: datetime | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PluginHistoryListResponse(BaseModel):
    items: list[PluginHistorySummary]


class PluginHistoryDetail(PluginHistorySummary):
    normalized_workspace_path: str | None
    model_id: str | None
    source_payload: dict[str, Any] | None


class PluginMessage(BaseModel):
    id: str
    seq: int
    message_type: str
    ask_type: str | None
    say_type: str | None
    text: str | None
    reasoning: str | None
    partial: bool
    occurred_at: datetime | None
    created_at: datetime


class PluginMessageListResponse(BaseModel):
    items: list[PluginMessage]


class PluginEvent(BaseModel):
    id: str
    seq: int
    source: str
    event_family: str
    event_type: str
    status: str | None
    title: str | None
    text: str | None
    tool_name: str | None
    command: str | None
    exit_code: int | None
    occurred_at: datetime | None
    created_at: datetime


class PluginEventListResponse(BaseModel):
    items: list[PluginEvent]


class PluginFileChange(BaseModel):
    id: str
    file_path: str
    change_type: str
    content_preview: str | None
    read_line_start: int | None
    read_line_end: int | None
    operation_is_located_in_workspace: bool | None
    created_at: datetime


class PluginFileListResponse(BaseModel):
    items: list[PluginFileChange]
