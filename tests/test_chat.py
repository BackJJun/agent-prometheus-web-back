import asyncio
from uuid import uuid4

import asyncpg
import httpx
from fastapi.testclient import TestClient

from app.main import app

TEST_TITLE_PREFIX = "pytest web chat"


def _get_keycloak_access_token() -> str:
    response = httpx.post(
        "http://localhost:18080/realms/agent-pmts/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "agent-pmts-web",
            "username": "dev@prometheus.local",
            "password": "dev5748#@12",
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


async def _cleanup_chat_rows() -> None:
    connection = await _connect()
    try:
        session_ids = await connection.fetch(
            "select id from web_chat_sessions where title like $1",
            f"{TEST_TITLE_PREFIX}%",
        )
        ids = [row["id"] for row in session_ids]
        if ids:
            await connection.execute(
                "delete from web_chat_references where message_id = any(select id from web_chat_messages where session_id = any($1::uuid[]))",
                ids,
            )
            await connection.execute(
                "delete from web_tool_calls where session_id = any($1::uuid[])", ids
            )
            await connection.execute(
                "delete from web_chat_attachments where session_id = any($1::uuid[])", ids
            )
            await connection.execute(
                "delete from web_chat_messages where session_id = any($1::uuid[])", ids
            )
            await connection.execute(
                "delete from web_chat_sessions where id = any($1::uuid[])", ids
            )
    finally:
        await connection.close()


def test_web_chat_session_create_list_and_detail() -> None:
    asyncio.run(_cleanup_chat_rows())
    client = TestClient(app)
    title = f"{TEST_TITLE_PREFIX} {uuid4()}"

    try:
        create_response = client.post(
            "/api/chat/sessions", json={"title": title}, headers=_auth_headers()
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["title"] == title
        assert created["status"] == "active"

        list_response = client.get("/api/chat/sessions", headers=_auth_headers())
        assert list_response.status_code == 200
        assert any(session["id"] == created["id"] for session in list_response.json()["items"])

        detail_response = client.get(f"/api/chat/sessions/{created['id']}", headers=_auth_headers())
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == created["id"]
    finally:
        asyncio.run(_cleanup_chat_rows())


def test_web_chat_message_create_stores_user_message_and_assistant_placeholder() -> None:
    asyncio.run(_cleanup_chat_rows())
    client = TestClient(app)
    title = f"{TEST_TITLE_PREFIX} {uuid4()}"

    try:
        session_response = client.post(
            "/api/chat/sessions", json={"title": title}, headers=_auth_headers()
        )
        session_id = session_response.json()["id"]

        message_response = client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"content": "안녕하세요. 프로젝트 상태를 요약해줘."},
            headers=_auth_headers(),
        )

        assert message_response.status_code == 201
        body = message_response.json()
        assert body["user_message"]["role"] == "user"
        assert body["user_message"]["content"] == "안녕하세요. 프로젝트 상태를 요약해줘."
        assert body["assistant_message"]["role"] == "assistant"
        assert body["assistant_message"]["status"] == "pending"

        messages_response = client.get(
            f"/api/chat/sessions/{session_id}/messages", headers=_auth_headers()
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()["items"]
        assert [message["role"] for message in messages] == ["user", "assistant"]
    finally:
        asyncio.run(_cleanup_chat_rows())


def test_web_chat_filters_other_user_sessions_and_archives_current_session() -> None:
    asyncio.run(_cleanup_chat_rows())
    client = TestClient(app)
    title = f"{TEST_TITLE_PREFIX} {uuid4()}"

    try:
        session_response = client.post(
            "/api/chat/sessions", json={"title": title}, headers=_auth_headers()
        )
        session = session_response.json()
        other_title = f"{TEST_TITLE_PREFIX} other {uuid4()}"
        asyncio.run(_insert_other_user_session(session["workspace_id"], other_title))

        list_response = client.get("/api/chat/sessions", headers=_auth_headers())
        assert list_response.status_code == 200
        titles = [item["title"] for item in list_response.json()["items"]]
        assert title in titles
        assert other_title not in titles

        archive_response = client.post(
            f"/api/chat/sessions/{session['id']}/archive", headers=_auth_headers()
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"

        archived_detail = client.get(f"/api/chat/sessions/{session['id']}", headers=_auth_headers())
        assert archived_detail.status_code == 404
    finally:
        asyncio.run(_cleanup_chat_rows())


async def _insert_other_user_session(workspace_id: str, title: str) -> None:
    connection = await _connect()
    other_user_id = uuid4()
    try:
        await connection.execute(
            """
            insert into users (id, email, name)
            values ($1, $2, $3)
            """,
            other_user_id,
            f"other-{other_user_id}@example.test",
            "Other Test User",
        )
        await connection.execute(
            """
            insert into web_chat_sessions (workspace_id, user_id, title, mode, status, payload)
            values ($1, $2, $3, 'chat', 'active', '{}'::jsonb)
            """,
            workspace_id,
            other_user_id,
            title,
        )
    finally:
        await connection.close()
