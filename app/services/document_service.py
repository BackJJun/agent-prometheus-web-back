from typing import Any, Literal
from uuid import UUID

from sqlalchemy import text

from app.core.database import get_sessionmaker
from app.services.chat_service import ensure_default_workspace


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


async def list_documents(kind: Literal["general", "code"]) -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        if kind == "code":
            rows = await session.execute(
                text(
                    """
                    select 'code' as kind,
                           id::text,
                           workspace_id::text,
                           repository_id::text,
                           connection_id::text,
                           branch_name,
                           commit_sha,
                           status,
                           current_step,
                           progress,
                           error_message,
                           created_at
                    from code_index_jobs
                    order by created_at desc
                    limit 50
                    """
                )
            )
            return [_row_to_dict(row) for row in rows]
        rows = await session.execute(
            text(
                """
                select 'general' as kind,
                       id::text,
                       workspace_id::text,
                       title,
                       file_name,
                       file_type,
                       mime_type,
                       storage_uri,
                       visibility,
                       owner_id::text,
                       indexing_status,
                       latest_version_id::text,
                       created_at,
                       updated_at
                from documents
                order by updated_at desc
                limit 50
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def create_document(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    workspace_id = await ensure_default_workspace(user_id)
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        document = (
            await session.execute(
                text(
                    """
                    insert into documents (
                        workspace_id, title, file_name, file_type, mime_type,
                        storage_uri, visibility, owner_id, indexing_status, payload
                    )
                    values (
                        :workspace_id, :title, :file_name, :file_type, :mime_type,
                        :storage_uri, :visibility, :owner_id, 'pending', '{}'::jsonb
                    )
                    returning id::text
                    """
                ),
                {**data, "workspace_id": workspace_id, "owner_id": user_id},
            )
        ).one()
        document_id = document._mapping["id"]
        version = (
            await session.execute(
                text(
                    """
                    insert into document_versions (
                        document_id, version_no, storage_uri,
                        chunk_count, token_count, created_by, payload
                    )
                    values (:document_id, 1, :storage_uri, 0, 0, :created_by, '{}'::jsonb)
                    returning id::text
                    """
                ),
                {
                    "document_id": document_id,
                    "storage_uri": data["storage_uri"],
                    "created_by": user_id,
                },
            )
        ).one()
        version_id = version._mapping["id"]
        await session.execute(
            text("update documents set latest_version_id = :version_id where id = :document_id"),
            {"version_id": version_id, "document_id": document_id},
        )
        await session.execute(
            text(
                """
                insert into document_index_jobs (
                    workspace_id, document_id, version_id, status, current_step, progress, payload
                )
                values (
                    :workspace_id, :document_id, :version_id,
                    'pending', 'queued', 0, '{}'::jsonb
                )
                """
            ),
            {"workspace_id": workspace_id, "document_id": document_id, "version_id": version_id},
        )
        await session.commit()
        return await get_document(UUID(document_id))  # type: ignore[return-value]


async def get_document(document_id: UUID) -> dict[str, Any] | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    select 'general' as kind,
                           id::text,
                           workspace_id::text,
                           title,
                           file_name,
                           file_type,
                           mime_type,
                           storage_uri,
                           visibility,
                           owner_id::text,
                           indexing_status,
                           latest_version_id::text,
                           created_at,
                           updated_at
                    from documents
                    where id = :document_id
                    """
                ),
                {"document_id": str(document_id)},
            )
        ).first()
        return _row_to_dict(row) if row else None


async def list_document_versions(document_id: UUID) -> list[dict[str, Any]] | None:
    if await get_document(document_id) is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       document_id::text,
                       version_no,
                       storage_uri,
                       file_size_bytes,
                       checksum_sha256,
                       parser_name,
                       parser_version,
                       chunk_count,
                       token_count,
                       created_by::text,
                       created_at
                from document_versions
                where document_id = :document_id
                order by version_no desc
                """
            ),
            {"document_id": str(document_id)},
        )
        return [_row_to_dict(row) for row in rows]


async def list_index_jobs(kind: Literal["general", "code"]) -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        if kind == "code":
            rows = await session.execute(
                text(
                    """
                    select 'code' as kind,
                           id::text,
                           workspace_id::text,
                           status,
                           current_step,
                           progress,
                           error_message,
                           created_at,
                           null::text as document_id,
                           null::text as version_id,
                           repository_id::text,
                           connection_id::text,
                           branch_name,
                           commit_sha
                    from code_index_jobs
                    order by created_at desc
                    limit 50
                    """
                )
            )
            return [_row_to_dict(row) for row in rows]
        rows = await session.execute(
            text(
                """
                select 'general' as kind,
                       id::text,
                       workspace_id::text,
                       status,
                       current_step,
                       progress,
                       error_message,
                       created_at,
                       document_id::text,
                       version_id::text,
                       null::text as repository_id,
                       null::text as connection_id,
                       null::text as branch_name,
                       null::text as commit_sha
                from document_index_jobs
                order by created_at desc
                limit 50
                """
            )
        )
        return [_row_to_dict(row) for row in rows]
