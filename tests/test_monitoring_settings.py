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
            "username": "admin",
            "password": "12345",
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


def test_llm_provider_and_model_can_be_registered() -> None:
    asyncio.run(_cleanup_settings_rows())
    client = TestClient(app)
    provider_name = f"{TEST_SETTINGS_PREFIX}-{uuid4()}"

    try:
        provider_response = client.post(
            "/api/settings/llm-providers",
            headers=_auth_headers(),
            json={
                "provider": provider_name,
                "base_url": "http://llm.local",
                "api_key": "secret-test-key",
                "status": "active",
            },
        )

        assert provider_response.status_code == 201
        provider = provider_response.json()
        assert provider["provider"] == provider_name
        assert provider["base_url"] == "http://llm.local"
        assert "api_key" not in provider
        assert "config" not in provider

        model_response = client.post(
            "/api/settings/llm-models",
            headers=_auth_headers(),
            json={
                "provider_id": provider["id"],
                "name": "Qwen Coder",
                "model_key": "qwen-coder",
                "context_window": 32768,
                "enabled": True,
                "status": "active",
            },
        )

        assert model_response.status_code == 201
        model = model_response.json()
        assert model["provider_id"] == provider["id"]
        assert model["name"] == "Qwen Coder"
        assert model["model_key"] == "qwen-coder"
        assert model["context_window"] == 32768
        assert model["enabled"] is True

        models = client.get("/api/settings/llm-models", headers=_auth_headers())
        assert models.status_code == 200
        assert any(item["model_key"] == "qwen-coder" for item in models.json()["items"])
    finally:
        asyncio.run(_cleanup_settings_rows())
