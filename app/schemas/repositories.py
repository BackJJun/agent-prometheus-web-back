from datetime import datetime

from pydantic import BaseModel


class RepositoryProviderResponse(BaseModel):
    id: str
    workspace_id: str
    provider: str
    name: str
    base_url: str
    status: str
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RepositoryProviderListResponse(BaseModel):
    items: list[RepositoryProviderResponse]


class RepositoryGroupResponse(BaseModel):
    id: str
    provider_id: str
    provider_group_id: str | None
    name: str
    full_path: str
    parent_group_id: str | None
    visibility: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RepositoryGroupListResponse(BaseModel):
    items: list[RepositoryGroupResponse]


class RepositoryConnectionResponse(BaseModel):
    id: str
    workspace_id: str
    repository_id: str
    provider_id: str
    group_id: str | None
    provider_repository_id: str | None
    name: str
    full_name: str
    default_branch: str | None
    clone_url: str | None
    web_url: str | None
    status: str
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RepositoryConnectionListResponse(BaseModel):
    items: list[RepositoryConnectionResponse]


class RepositoryBranchResponse(BaseModel):
    id: str
    connection_id: str
    name: str
    commit_sha: str | None
    is_default: bool
    protected: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RepositoryBranchListResponse(BaseModel):
    items: list[RepositoryBranchResponse]


class RepositoryCommitResponse(BaseModel):
    id: str
    connection_id: str
    branch_name: str | None
    commit_sha: str
    parent_shas: list[str]
    author_name: str | None
    author_email: str | None
    committed_at: datetime | None
    message: str
    web_url: str | None
    created_at: datetime


class RepositoryCommitListResponse(BaseModel):
    items: list[RepositoryCommitResponse]
