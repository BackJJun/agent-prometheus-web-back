from pydantic import BaseModel, Field


class LogFileSummary(BaseModel):
    file_name: str
    size_bytes: int = Field(ge=0)
    modified_at: str


class LogFileListResponse(BaseModel):
    items: list[LogFileSummary]


class LogFileContentResponse(BaseModel):
    file_name: str
    lines: list[str]
