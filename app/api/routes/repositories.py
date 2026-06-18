from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.repositories import (
    RepositoryBranchListResponse,
    RepositoryCommitListResponse,
    RepositoryConnectionListResponse,
    RepositoryConnectionResponse,
    RepositoryGroupListResponse,
    RepositoryProviderListResponse,
)
from app.services.repository_service import (
    get_repository_connection,
    list_repository_branches,
    list_repository_commits,
    list_repository_connections,
    list_repository_groups,
    list_repository_providers,
)

router = APIRouter(tags=["repositories"])


@router.get("/api/repository-providers", response_model=RepositoryProviderListResponse)
async def get_providers(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_repository_providers()}


@router.get("/api/repository-groups", response_model=RepositoryGroupListResponse)
async def get_groups(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_repository_groups()}


@router.get("/api/repository-connections", response_model=RepositoryConnectionListResponse)
async def get_connections(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_repository_connections()}


@router.get(
    "/api/repository-connections/{connection_id}", response_model=RepositoryConnectionResponse
)
async def get_connection(
    connection_id: UUID,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    connection = await get_repository_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Repository connection not found")
    return connection


@router.get(
    "/api/repository-connections/{connection_id}/branches",
    response_model=RepositoryBranchListResponse,
)
async def get_branches(
    connection_id: UUID,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    branches = await list_repository_branches(connection_id)
    if branches is None:
        raise HTTPException(status_code=404, detail="Repository connection not found")
    return {"items": branches}


@router.get(
    "/api/repository-connections/{connection_id}/commits",
    response_model=RepositoryCommitListResponse,
)
async def get_commits(
    connection_id: UUID,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    commits = await list_repository_commits(connection_id)
    if commits is None:
        raise HTTPException(status_code=404, detail="Repository connection not found")
    return {"items": commits}
