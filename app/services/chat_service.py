import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.core.database import get_sessionmaker
from app.llm import LLMProviderConfig, get_llm_provider

DEFAULT_ORG_SLUG = "default"
DEFAULT_WORKSPACE_SLUG = "personal"


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


def _chat_message_fields() -> str:
    return """
    id::text,
    session_id::text,
    parent_message_id::text,
    role,
    content,
    status,
    token_count,
    created_at
    """


async def ensure_default_workspace(user_id: str) -> str:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        org_id = await session.scalar(
            text(
                """
                insert into organizations (name, slug, payload)
                values ('Default Organization', :slug, '{}'::jsonb)
                on conflict (slug) do update set updated_at = now()
                returning id::text
                """
            ),
            {"slug": DEFAULT_ORG_SLUG},
        )
        workspace_id = await session.scalar(
            text(
                """
                insert into workspaces (org_id, name, slug, created_by, payload)
                values (:org_id, 'Personal Workspace', :slug, :user_id, '{}'::jsonb)
                on conflict (org_id, slug) do update set updated_at = now()
                returning id::text
                """
            ),
            {"org_id": org_id, "slug": DEFAULT_WORKSPACE_SLUG, "user_id": user_id},
        )
        await session.execute(
            text(
                """
                insert into workspace_members (workspace_id, user_id)
                values (:workspace_id, :user_id)
                on conflict (workspace_id, user_id) do update set status = 'active'
                """
            ),
            {"workspace_id": workspace_id, "user_id": user_id},
        )
        await session.commit()
        return str(workspace_id)


async def list_chat_sessions(user_id: str) -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       title,
                       mode,
                       status,
                       last_message_at,
                       created_at,
                       updated_at
                from web_chat_sessions
                where user_id = :user_id and status = 'active'
                order by updated_at desc
                """
            ),
            {"user_id": user_id},
        )
        return [_row_to_dict(row) for row in rows]


async def create_chat_session(user_id: str, title: str, mode: str) -> dict[str, Any]:
    workspace_id = await ensure_default_workspace(user_id)
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    insert into web_chat_sessions (
                        workspace_id, user_id, title, mode, status, payload
                    )
                    values (:workspace_id, :user_id, :title, :mode, 'active', '{}'::jsonb)
                    returning id::text,
                              workspace_id::text,
                              title,
                              mode,
                              status,
                              last_message_at,
                              created_at,
                              updated_at
                    """
                ),
                {"workspace_id": workspace_id, "user_id": user_id, "title": title, "mode": mode},
            )
        ).one()
        await session.commit()
        return _row_to_dict(row)


async def get_chat_session(user_id: str, session_id: UUID) -> dict[str, Any] | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    select id::text,
                           workspace_id::text,
                           title,
                           mode,
                           status,
                           last_message_at,
                           created_at,
                           updated_at
                    from web_chat_sessions
                    where id = :session_id and user_id = :user_id and status = 'active'
                    """
                ),
                {"session_id": str(session_id), "user_id": user_id},
            )
        ).first()
        return _row_to_dict(row) if row else None


async def archive_chat_session(user_id: str, session_id: UUID) -> dict[str, Any] | None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    """
                    update web_chat_sessions
                    set status = 'archived', updated_at = now()
                    where id = :session_id and user_id = :user_id and status = 'active'
                    returning id::text,
                              workspace_id::text,
                              title,
                              mode,
                              status,
                              last_message_at,
                              created_at,
                              updated_at
                    """
                ),
                {"session_id": str(session_id), "user_id": user_id},
            )
        ).first()
        await session.commit()
        return _row_to_dict(row) if row else None


async def list_chat_messages(user_id: str, session_id: UUID) -> list[dict[str, Any]] | None:
    if await get_chat_session(user_id, session_id) is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       session_id::text,
                       parent_message_id::text,
                       role,
                       content,
                       status,
                       token_count,
                       created_at
                from web_chat_messages
                where session_id = :session_id
                order by created_at asc
                """
            ),
            {"session_id": str(session_id)},
        )
        return [_row_to_dict(row) for row in rows]


async def create_chat_message(
    user_id: str, session_id: UUID, content: str
) -> dict[str, Any] | None:
    if await get_chat_session(user_id, session_id) is None:
        return None
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user_message = (
            await session.execute(
                text(
                    """
                    insert into web_chat_messages (
                        session_id, role, content, status, token_count, payload
                    )
                    values (:session_id, 'user', :content, 'completed', 0, '{}'::jsonb)
                    returning id::text,
                              session_id::text,
                              parent_message_id::text,
                              role,
                              content,
                              status,
                              token_count,
                              created_at
                    """
                ),
                {"session_id": str(session_id), "content": content},
            )
        ).one()
        assistant_message = (
            await session.execute(
                text(
                    """
                    insert into web_chat_messages (
                        session_id, parent_message_id, role, content, status, token_count, payload
                    )
                    values (
                        :session_id, :parent_message_id, 'assistant', '', 'pending', 0, '{}'::jsonb
                    )
                    returning id::text,
                              session_id::text,
                              parent_message_id::text,
                              role,
                              content,
                              status,
                              token_count,
                              created_at
                    """
                ),
                {"session_id": str(session_id), "parent_message_id": user_message._mapping["id"]},
            )
        ).one()
        await session.execute(
            text(
                """
                update web_chat_sessions
                set last_message_at = now(), updated_at = now()
                where id = :session_id
                """
            ),
            {"session_id": str(session_id)},
        )
        await session.commit()
        return {
            "user_message": _row_to_dict(user_message),
            "assistant_message": _row_to_dict(assistant_message),
        }


async def create_chat_message_pair(
    user_id: str, session_id: UUID, content: str
) -> dict[str, Any] | None:
    if await get_chat_session(user_id, session_id) is None:
        return None

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user_message = (
            await session.execute(
                text(
                    f"""
                    insert into web_chat_messages (
                        session_id, role, content, status, token_count, payload
                    )
                    values (:session_id, 'user', :content, 'completed', 0, '{{}}'::jsonb)
                    returning {_chat_message_fields()}
                    """
                ),
                {"session_id": str(session_id), "content": content},
            )
        ).one()
        assistant_message = (
            await session.execute(
                text(
                    f"""
                    insert into web_chat_messages (
                        session_id, parent_message_id, role, content, status, token_count, payload
                    )
                    values (
                        :session_id,
                        :parent_message_id,
                        'assistant',
                        '',
                        'streaming',
                        0,
                        '{{}}'::jsonb
                    )
                    returning {_chat_message_fields()}
                    """
                ),
                {"session_id": str(session_id), "parent_message_id": user_message._mapping["id"]},
            )
        ).one()
        await session.execute(
            text(
                """
                update web_chat_sessions
                set last_message_at = now(), updated_at = now()
                where id = :session_id
                """
            ),
            {"session_id": str(session_id)},
        )
        await session.commit()
        return {
            "user_message": _row_to_dict(user_message),
            "assistant_message": _row_to_dict(assistant_message),
        }


async def complete_assistant_message(
    message_id: str, content: str, status: str = "completed"
) -> None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                update web_chat_messages
                set content = :content,
                    status = :status,
                    token_count = :token_count
                where id = :message_id
                """
            ),
            {
                "message_id": message_id,
                "content": content,
                "status": status,
                "token_count": len(content.split()),
            },
        )
        await session.execute(
            text(
                """
                update web_chat_sessions
                set last_message_at = now(), updated_at = now()
                where id = (
                    select session_id from web_chat_messages where id = :message_id
                )
                """
            ),
            {"message_id": message_id},
        )
        await session.commit()


async def get_llm_config_for_chat(
    user_id: str, provider: str | None = None, model: str | None = None
) -> LLMProviderConfig | None:
    workspace_id = await ensure_default_workspace(user_id)
    provider_filter = "and p.provider = :provider" if provider else ""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = (
            await session.execute(
                text(
                    f"""
                    select p.provider,
                           p.base_url,
                           p.config ->> 'api_key' as api_key,
                           m.model_key
                    from llm_providers p
                    left join llm_models m
                      on m.provider_id = p.id
                     and m.enabled = true
                     and m.status = 'active'
                    where p.workspace_id = :workspace_id
                      and p.status = 'active'
                      {provider_filter}
                    order by m.updated_at desc nulls last, p.updated_at desc
                    limit 1
                    """
                ),
                {"workspace_id": workspace_id, "provider": provider},
            )
        ).first()

    if row is None:
        return None

    data = row._mapping
    model_key = data["model_key"] or model
    if not model_key:
        default_models = {
            "openai": "gpt-4o-mini",
            "vllm": "default",
            "claude": "claude-3-5-haiku-latest",
            "anthropic": "claude-3-5-haiku-latest",
            "gemini": "gemini-1.5-flash",
            "google": "gemini-1.5-flash",
        }
        model_key = default_models.get(str(data["provider"]).lower(), "default")

    return LLMProviderConfig(
        provider=str(data["provider"]),
        model=str(model_key),
        base_url=data["base_url"],
        api_key=data["api_key"],
    )


async def stream_chat_markdown(
    user_id: str,
    session_id: UUID,
    content: str,
    provider: str | None = None,
    model: str | None = None,
):
    messages = await create_chat_message_pair(user_id, session_id, content)
    if messages is None:
        return None

    config = await get_llm_config_for_chat(user_id, provider, model)
    llm_provider = get_llm_provider(config)

    async def stream():
        import json

        assistant_message = messages["assistant_message"]
        yield json.dumps({"type": "messages", **messages}, default=str, ensure_ascii=False) + "\n"

        chunks: list[str] = []
        try:
            async with asyncio.timeout(60):
                async for chunk in llm_provider.stream_markdown(content):
                    chunks.append(chunk)
                    yield json.dumps({"type": "delta", "content": chunk}, ensure_ascii=False) + "\n"

            final_content = "".join(chunks)
            await complete_assistant_message(assistant_message["id"], final_content)
            yield json.dumps(
                {
                    "type": "done",
                    "assistant_message": {
                        **assistant_message,
                        "content": final_content,
                        "status": "completed",
                    },
                },
                default=str,
                ensure_ascii=False,
            ) + "\n"
        except Exception as exc:
            error_content = f"## 오류\n\nLLM 응답 생성 중 오류가 발생했습니다.\n\n`{exc}`"
            await complete_assistant_message(assistant_message["id"], error_content, "failed")
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(exc),
                    "assistant_message": {
                        **assistant_message,
                        "content": error_content,
                        "status": "failed",
                    },
                },
                default=str,
                ensure_ascii=False,
            ) + "\n"

    return stream()
