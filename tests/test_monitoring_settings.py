import asyncio
from uuid import uuid4

import asyncpg
import httpx
from fastapi.testclient import TestClient

from app.main import app

TEST_SETTINGS_PREFIX = "pytest-settings"


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


async def _cleanup_settings_rows() -> None:
    connection = await _connect()
    try:
        provider_rows = await connection.fetch(
            "select id from llm_providers where provider like $1", f"{TEST_SETTINGS_PREFIX}%"
        )
        provider_ids = [row["id"] for row in provider_rows]
        if provider_ids:
            await connection.execute(
                "delete from llm_models where provider_id = any($1::uuid[])", provider_ids
            )
            await connection.execute(
                "delete from llm_providers where id = any($1::uuid[])", provider_ids
            )
        await connection.execute(
            "delete from monitoring_events where service like $1", f"{TEST_SETTINGS_PREFIX}%"
        )
        await connection.execute(
            "delete from service_health_checks where service_name like $1",
            f"{TEST_SETTINGS_PREFIX}%",
        )
        await connection.execute(
            "delete from notification_settings where target like $1", f"{TEST_SETTINGS_PREFIX}%"
        )
    finally:
        await connection.close()


async def _insert_monitoring_and_settings_fixture() -> None:
    connection = await _connect()
    slug = f"{TEST_SETTINGS_PREFIX}-{uuid4()}"
    try:
        org_id = await connection.fetchval(
            "insert into organizations (name, slug) values ($1, $2) returning id", slug, slug
        )
        workspace_id = await connection.fetchval(
            "insert into workspaces (org_id, name, slug) values ($1, $2, $3) returning id",
            org_id,
            slug,
            slug,
        )
        await connection.execute(
            "insert into monitoring_events (workspace_id, level, service, message, payload) values ($1, 'warn', $2, '테스트 경고', '{}'::jsonb)",
            workspace_id,
            slug,
        )
        await connection.execute(
            "insert into service_health_checks (workspace_id, service_name, status, latency_ms, payload) values ($1, $2, 'healthy', 12, '{}'::jsonb)",
            workspace_id,
            slug,
        )
        provider_id = await connection.fetchval(
            "insert into llm_providers (workspace_id, provider, base_url, status, config) values ($1, $2, 'http://llm.local', 'active', '{}'::jsonb) returning id",
            workspace_id,
            slug,
        )
        await connection.execute(
            "insert into llm_models (provider_id, name, model_key, context_window, enabled, status) values ($1, 'Qwen Test', 'qwen-test', 32768, true, 'active')",
            provider_id,
        )
        await connection.execute(
            "insert into notification_settings (workspace_id, channel, enabled, target, events) values ($1, 'email', true, $2, ARRAY['indexing_failed']::text[])",
            workspace_id,
            slug,
        )
    finally:
        await connection.close()


def test_monitoring_and_settings_empty_lists_are_renderable() -> None:
    asyncio.run(_cleanup_settings_rows())
    client = TestClient(app)

    for path in [
        "/api/monitoring/events",
        "/api/monitoring/health-checks",
        "/api/settings/llm-providers",
        "/api/settings/llm-models",
        "/api/settings/notification-settings",
    ]:
        response = client.get(path, headers=_auth_headers())
        assert response.status_code == 200
        assert "items" in response.json()


def test_monitoring_and_settings_return_inserted_rows() -> None:
    asyncio.run(_cleanup_settings_rows())
    client = TestClient(app)

    try:
        asyncio.run(_insert_monitoring_and_settings_fixture())

        events = client.get("/api/monitoring/events", headers=_auth_headers())
        assert events.status_code == 200
        assert any(item["message"] == "테스트 경고" for item in events.json()["items"])

        health_checks = client.get("/api/monitoring/health-checks", headers=_auth_headers())
        assert health_checks.status_code == 200
        assert any(item["status"] == "healthy" for item in health_checks.json()["items"])

        providers = client.get("/api/settings/llm-providers", headers=_auth_headers())
        assert providers.status_code == 200
        assert any(
            item["provider"].startswith(TEST_SETTINGS_PREFIX) for item in providers.json()["items"]
        )

        models = client.get("/api/settings/llm-models", headers=_auth_headers())
        assert models.status_code == 200
        assert any(item["model_key"] == "qwen-test" for item in models.json()["items"])

        notifications = client.get("/api/settings/notification-settings", headers=_auth_headers())
        assert notifications.status_code == 200
        assert any(
            item["target"].startswith(TEST_SETTINGS_PREFIX)
            for item in notifications.json()["items"]
        )
    finally:
        asyncio.run(_cleanup_settings_rows())
