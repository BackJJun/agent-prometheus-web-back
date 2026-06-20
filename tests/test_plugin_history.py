import asyncio
from uuid import uuid4

import asyncpg
import httpx
from fastapi.testclient import TestClient

from app.main import app

TEST_TASK_ID_PREFIX = "pytest-plugin-history"


def _get_keycloak_access_token() -> str:
    response = httpx.post(
        "http://localhost:18080/realms/agent-pmts/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "agent-pmts-web",
            "username": "admin",
            "password": "1234",
            "scope": "openid profile email",
        },
        timeout=10,
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_keycloak_access_token()}"}


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        user="crux",
        password="crux5748#@12",
        database="agent_pmts",
        host="localhost",
        port=5432,
    )


async def _cleanup_plugin_rows() -> None:
    connection = await _connect()
    try:
        rows = await connection.fetch(
            "select id from plg_tasks where task_id like $1", f"{TEST_TASK_ID_PREFIX}%"
        )
        ids = [row["id"] for row in rows]
        if ids:
            await connection.execute(
                "delete from plg_task_file_changes where plg_task_id = any($1::uuid[])", ids
            )
            await connection.execute(
                "delete from plg_task_events where plg_task_id = any($1::uuid[])", ids
            )
            await connection.execute(
                "delete from plg_api_conversation_messages where plg_task_id = any($1::uuid[])", ids
            )
            await connection.execute(
                "delete from plg_ui_messages where plg_task_id = any($1::uuid[])", ids
            )
            await connection.execute("delete from plg_tasks where id = any($1::uuid[])", ids)
    finally:
        await connection.close()


async def _insert_plugin_history() -> str:
    connection = await _connect()
    task_id = f"{TEST_TASK_ID_PREFIX}-{uuid4()}"
    try:
        row = await connection.fetchrow(
            """
            insert into plg_tasks (task_id, source, title, task, status, mode, workspace_path, source_payload)
            values ($1, 'plugin', '테스트 플러그인 작업', '코드를 리팩토링해줘', 'completed', 'agent', 'C:\\workspace\\sample', '{}'::jsonb)
            returning id
            """,
            task_id,
        )
        plg_task_id = row["id"]
        await connection.execute(
            """
            insert into plg_ui_messages (plg_task_id, seq, message_type, say_type, text, partial, raw_message)
            values ($1, 1, 'say', 'text', '분석을 시작합니다.', false, '{}'::jsonb)
            """,
            plg_task_id,
        )
        await connection.execute(
            """
            insert into plg_task_events (plg_task_id, seq, source, event_family, event_type, status, title, text, payload)
            values ($1, 1, 'plugin', 'tool', 'read_file', 'completed', '파일 읽기', 'README.md 확인', '{}'::jsonb)
            """,
            plg_task_id,
        )
        await connection.execute(
            """
            insert into plg_task_file_changes (plg_task_id, file_path, change_type, content_preview, raw_payload)
            values ($1, 'README.md', 'read', 'sample preview', '{}'::jsonb)
            """,
            plg_task_id,
        )
        return task_id
    finally:
        await connection.close()


def test_plugin_histories_return_empty_items_without_plugin_data() -> None:
    asyncio.run(_cleanup_plugin_rows())
    client = TestClient(app)

    response = client.get("/api/plugin-histories", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_plugin_history_detail_messages_events_and_files_are_read_only() -> None:
    asyncio.run(_cleanup_plugin_rows())
    client = TestClient(app)

    try:
        task_id = asyncio.run(_insert_plugin_history())

        list_response = client.get("/api/plugin-histories", headers=_auth_headers())
        assert list_response.status_code == 200
        assert any(item["task_id"] == task_id for item in list_response.json()["items"])

        detail_response = client.get(f"/api/plugin-histories/{task_id}", headers=_auth_headers())
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["task_id"] == task_id
        assert detail["workspace_path"] == "C:\\workspace\\sample"

        messages_response = client.get(
            f"/api/plugin-histories/{task_id}/messages", headers=_auth_headers()
        )
        assert messages_response.status_code == 200
        assert messages_response.json()["items"][0]["text"] == "분석을 시작합니다."

        events_response = client.get(
            f"/api/plugin-histories/{task_id}/events", headers=_auth_headers()
        )
        assert events_response.status_code == 200
        assert events_response.json()["items"][0]["event_family"] == "tool"

        files_response = client.get(
            f"/api/plugin-histories/{task_id}/files", headers=_auth_headers()
        )
        assert files_response.status_code == 200
        assert files_response.json()["items"][0]["file_path"] == "README.md"

        write_response = client.post(
            f"/api/plugin-histories/{task_id}/messages", headers=_auth_headers()
        )
        assert write_response.status_code == 405
    finally:
        asyncio.run(_cleanup_plugin_rows())


def test_plugin_history_missing_task_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/plugin-histories/not-found", headers=_auth_headers())

    assert response.status_code == 404
