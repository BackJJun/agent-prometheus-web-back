from typing import Any

from sqlalchemy import text

from app.core.database import get_sessionmaker


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


async def list_llm_providers() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       provider,
                       base_url,
                       status,
                       created_at,
                       updated_at
                from llm_providers
                order by updated_at desc
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def list_llm_models() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       provider_id::text,
                       name,
                       model_key,
                       context_window,
                       enabled,
                       status,
                       created_at,
                       updated_at
                from llm_models
                order by updated_at desc
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def list_notification_settings() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       channel,
                       enabled,
                       target,
                       events,
                       created_at,
                       updated_at
                from notification_settings
                order by updated_at desc
                """
            )
        )
        return [_row_to_dict(row) for row in rows]
