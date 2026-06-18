from datetime import datetime

from pydantic import BaseModel


class DashboardCounts(BaseModel):
    web_chats: int
    plugin_tasks: int
    general_docs_indexed: int
    code_docs_indexed: int
    repository_connections: int


class RecentPluginFailure(BaseModel):
    id: str
    source: str | None
    status: str
    failed_tasks: int | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class RecentDocumentJob(BaseModel):
    id: str
    document_id: str | None
    status: str
    current_step: str | None
    progress: int | None
    error_message: str | None
    created_at: datetime | None


class RecentCommit(BaseModel):
    id: str
    connection_id: str
    branch_name: str | None
    commit_sha: str
    author_name: str | None
    committed_at: datetime | None
    message: str | None
    web_url: str | None


class DashboardSummaryResponse(BaseModel):
    counts: DashboardCounts
    recent_plugin_failures: list[RecentPluginFailure]
    recent_document_jobs: list[RecentDocumentJob]
    recent_commits: list[RecentCommit]
