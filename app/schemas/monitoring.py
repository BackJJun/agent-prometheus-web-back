from datetime import datetime

from pydantic import BaseModel


class MonitoringEventResponse(BaseModel):
    id: str
    workspace_id: str | None
    level: str
    service: str
    message: str
    detail: str | None
    created_at: datetime


class MonitoringEventListResponse(BaseModel):
    items: list[MonitoringEventResponse]


class ServiceHealthCheckResponse(BaseModel):
    id: str
    workspace_id: str | None
    service_name: str
    status: str
    latency_ms: int | None
    error_rate: float | None
    checked_at: datetime


class ServiceHealthCheckListResponse(BaseModel):
    items: list[ServiceHealthCheckResponse]
