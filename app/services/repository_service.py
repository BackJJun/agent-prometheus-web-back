from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.core.database import get_sessionmaker


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


async def list_repository_providers() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       provider,
                       name,
                       base_url,
                       status,
                       last_synced_at,
                       created_at,
                       updated_at
                from repository_providers
                order by updated_at desc
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def list_repository_groups() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       provider_id::text,
                       provider_group_id,
                       name,
                       full_path,
                       parent_group_id::text,
                       visibility,
                       last_synced_at,
                       created_at,
                       updated_at
                from repository_groups
                order by updated_at desc
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def list_repository_connections() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       repository_id::text,
                       provider_id::text,
                       group_id::text,
                       provider_repository_id,
                       name,
                       full_name,
                       default_branch,
                       clone_url,
                       web_url,
                       status,
                       last_synced_at,
                       created_at,
                       updated_at
                from repository_connections
                order by updated_at desc
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def get_repository_connection(connection_id: UUID) -> dict[str, Any] | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    select id::text,
                           workspace_id::text,
                           repository_id::text,
                           provider_id::text,
                           group_id::text,
                           provider_repository_id,
                           name,
                           full_name,
                           default_branch,
                           clone_url,
                           web_url,
                           status,
                           last_synced_at,
                           created_at,
                           updated_at
                    from repository_connections
                    where id = :connection_id
                    """
                ),
                {"connection_id": str(connection_id)},
            )
        ).first()
        return _row_to_dict(row) if row else None


async def list_repository_branches(connection_id: UUID) -> list[dict[str, Any]] | None:
    if await get_repository_connection(connection_id) is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       connection_id::text,
                       name,
                       commit_sha,
                       is_default,
                       protected,
                       last_synced_at,
                       created_at,
                       updated_at
                from repository_branches
                where connection_id = :connection_id
                order by is_default desc, name asc
                """
            ),
            {"connection_id": str(connection_id)},
        )
        return [_row_to_dict(row) for row in rows]


async def list_repository_commits(connection_id: UUID) -> list[dict[str, Any]] | None:
    if await get_repository_connection(connection_id) is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       connection_id::text,
                       branch_name,
                       commit_sha,
                       parent_shas,
                       author_name,
                       author_email,
                       committed_at,
                       message,
                       web_url,
                       created_at
                from repository_commits
                where connection_id = :connection_id
                order by committed_at desc nulls last, created_at desc
                limit 100
                """
            ),
            {"connection_id": str(connection_id)},
        )
        return [_row_to_dict(row) for row in rows]
