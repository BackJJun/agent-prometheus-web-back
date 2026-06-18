from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    file_name: str = Field(min_length=1, max_length=500)
    file_type: str = Field(min_length=1, max_length=100)
    mime_type: str | None = None
    storage_uri: str = Field(min_length=1)
    visibility: Literal["private", "workspace", "org", "public"] = "workspace"


class GeneralDocumentResponse(BaseModel):
    kind: Literal["general"] = "general"
    id: str
    workspace_id: str
    title: str
    file_name: str
    file_type: str
    mime_type: str | None
    storage_uri: str
    visibility: str
    owner_id: str | None
    indexing_status: str
    latest_version_id: str | None
    created_at: datetime
    updated_at: datetime


class CodeDocumentResponse(BaseModel):
    kind: Literal["code"] = "code"
    id: str
    workspace_id: str
    repository_id: str | None
    connection_id: str | None
    branch_name: str
    commit_sha: str | None
    status: str
    current_step: str | None
    progress: int
    error_message: str | None
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[GeneralDocumentResponse] | list[CodeDocumentResponse]


class DocumentVersionResponse(BaseModel):
    id: str
    document_id: str
    version_no: int
    storage_uri: str
    file_size_bytes: int | None
    checksum_sha256: str | None
    parser_name: str | None
    parser_version: str | None
    chunk_count: int
    token_count: int
    created_by: str | None
    created_at: datetime


class DocumentVersionListResponse(BaseModel):
    items: list[DocumentVersionResponse]


class IndexJobResponse(BaseModel):
    kind: Literal["general", "code"]
    id: str
    workspace_id: str
    status: str
    current_step: str | None
    progress: int
    error_message: str | None
    created_at: datetime
    document_id: str | None = None
    version_id: str | None = None
    repository_id: str | None = None
    connection_id: str | None = None
    branch_name: str | None = None
    commit_sha: str | None = None


class IndexJobListResponse(BaseModel):
    items: list[IndexJobResponse]
