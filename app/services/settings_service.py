import json
from typing import Any

from sqlalchemy import text

from app.core.database import get_sessionmaker
from app.services.chat_service import ensure_default_workspace


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


async def create_llm_provider(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    workspace_id = await ensure_default_workspace(user_id)
    config = {}
    if data.get("api_key"):
        config["api_key"] = data["api_key"]

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    insert into llm_providers (workspace_id, provider, base_url, status, config)
                    values (
                        :workspace_id,
                        :provider,
                        :base_url,
                        :status,
                        cast(:config as jsonb)
                    )
                    on conflict (workspace_id, provider) do update set
                        base_url = excluded.base_url,
                        status = excluded.status,
                        config = excluded.config,
                        updated_at = now()
                    returning id::text,
                              workspace_id::text,
                              provider,
                              base_url,
                              status,
                              created_at,
                              updated_at
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "provider": data["provider"],
                    "base_url": data.get("base_url"),
                    "status": data["status"],
                    "config": json.dumps(config),
                },
            )
        ).one()
        await session.commit()
        return _row_to_dict(row)


async def create_llm_model(user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    workspace_id = await ensure_default_workspace(user_id)
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        provider_id = await session.scalar(
            text(
                """
                select id::text
                from llm_providers
                where id = :provider_id and workspace_id = :workspace_id
                """
            ),
            {"provider_id": data["provider_id"], "workspace_id": workspace_id},
        )
        if provider_id is None:
            return None

        row = (
            await session.execute(
                text(
                    """
                    insert into llm_models (
                        provider_id, name, model_key, context_window, enabled, status
                    )
                    values (
                        :provider_id, :name, :model_key, :context_window, :enabled, :status
                    )
                    on conflict (provider_id, model_key) do update set
                        name = excluded.name,
                        context_window = excluded.context_window,
                        enabled = excluded.enabled,
                        status = excluded.status,
                        updated_at = now()
                    returning id::text,
                              provider_id::text,
                              name,
                              model_key,
                              context_window,
                              enabled,
                              status,
                              created_at,
                              updated_at
                    """
                ),
                data,
            )
        ).one()
        await session.commit()
        return _row_to_dict(row)


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
