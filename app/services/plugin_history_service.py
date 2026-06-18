from typing import Any

from sqlalchemy import text

from app.core.database import get_sessionmaker


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


async def list_plugin_histories() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       task_id,
                       source,
                       title,
                       task,
                       status,
                       mode,
                       workspace_path,
                       source_started_at,
                       source_updated_at,
                       last_synced_at,
                       created_at,
                       updated_at
                from plg_tasks
                order by updated_at desc
                limit 50
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def get_plugin_history(task_id: str) -> dict[str, Any] | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    select id::text,
                           task_id,
                           source,
                           title,
                           task,
                           status,
                           mode,
                           workspace_path,
                           normalized_workspace_path,
                           model_id,
                           source_started_at,
                           source_updated_at,
                           last_synced_at,
                           source_payload,
                           created_at,
                           updated_at
                    from plg_tasks
                    where task_id = :task_id
                    """
                ),
                {"task_id": task_id},
            )
        ).first()
        return _row_to_dict(row) if row else None


async def _get_plugin_task_pk(task_id: str) -> str | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        return await session.scalar(
            text("select id::text from plg_tasks where task_id = :task_id"), {"task_id": task_id}
        )


async def list_plugin_messages(task_id: str) -> list[dict[str, Any]] | None:
    plg_task_id = await _get_plugin_task_pk(task_id)
    if plg_task_id is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       seq,
                       message_type,
                       ask_type,
                       say_type,
                       text,
                       reasoning,
                       partial,
                       occurred_at,
                       created_at
                from plg_ui_messages
                where plg_task_id = :plg_task_id
                order by seq asc, created_at asc
                """
            ),
            {"plg_task_id": plg_task_id},
        )
        return [_row_to_dict(row) for row in rows]


async def list_plugin_events(task_id: str) -> list[dict[str, Any]] | None:
    plg_task_id = await _get_plugin_task_pk(task_id)
    if plg_task_id is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       seq,
                       source,
                       event_family,
                       event_type,
                       status,
                       title,
                       text,
                       tool_name,
                       command,
                       exit_code,
                       occurred_at,
                       created_at
                from plg_task_events
                where plg_task_id = :plg_task_id
                order by seq asc, created_at asc
                """
            ),
            {"plg_task_id": plg_task_id},
        )
        return [_row_to_dict(row) for row in rows]


async def list_plugin_files(task_id: str) -> list[dict[str, Any]] | None:
    plg_task_id = await _get_plugin_task_pk(task_id)
    if plg_task_id is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       file_path,
                       change_type,
                       content_preview,
                       read_line_start,
                       read_line_end,
                       operation_is_located_in_workspace,
                       created_at
                from plg_task_file_changes
                where plg_task_id = :plg_task_id
                order by created_at asc
                """
            ),
            {"plg_task_id": plg_task_id},
        )
        return [_row_to_dict(row) for row in rows]
