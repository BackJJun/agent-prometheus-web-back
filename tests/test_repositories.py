import asyncio
from uuid import uuid4

import asyncpg
import httpx
from fastapi.testclient import TestClient

from app.main import app

TEST_REPO_PREFIX = "pytest-repo"


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


async def _cleanup_repository_rows() -> None:
    connection = await _connect()
    try:
        provider_rows = await connection.fetch(
            "select id from repository_providers where name like $1", f"{TEST_REPO_PREFIX}%"
        )
        provider_ids = [row["id"] for row in provider_rows]
        if provider_ids:
            connection_rows = await connection.fetch(
                "select id, repository_id from repository_connections where provider_id = any($1::uuid[])",
                provider_ids,
            )
            connection_ids = [row["id"] for row in connection_rows]
            repository_ids = [row["repository_id"] for row in connection_rows]
            if connection_ids:
                await connection.execute(
                    "delete from repository_commits where connection_id = any($1::uuid[])",
                    connection_ids,
                )
                await connection.execute(
                    "delete from repository_branches where connection_id = any($1::uuid[])",
                    connection_ids,
                )
                await connection.execute(
                    "delete from repository_connections where id = any($1::uuid[])", connection_ids
                )
            await connection.execute(
                "delete from repository_groups where provider_id = any($1::uuid[])", provider_ids
            )
            if repository_ids:
                await connection.execute(
                    "delete from repositories where id = any($1::uuid[])", repository_ids
                )
            await connection.execute(
                "delete from repository_providers where id = any($1::uuid[])", provider_ids
            )
    finally:
        await connection.close()


async def _insert_repository_fixture() -> str:
    connection = await _connect()
    workspace_id = uuid4()
    provider_name = f"{TEST_REPO_PREFIX}-{uuid4()}"
    try:
        org_id = await connection.fetchval(
            "insert into organizations (name, slug) values ($1, $2) returning id",
            provider_name,
            provider_name,
        )
        workspace_id = await connection.fetchval(
            "insert into workspaces (org_id, name, slug) values ($1, $2, $3) returning id",
            org_id,
            provider_name,
            provider_name,
        )
        provider_id = await connection.fetchval(
            """
            insert into repository_providers (workspace_id, provider, name, base_url, status, config)
            values ($1, 'gitea', $2, 'http://gitea.local', 'active', '{}'::jsonb)
            returning id
            """,
            workspace_id,
            provider_name,
        )
        group_id = await connection.fetchval(
            """
            insert into repository_groups (provider_id, provider_group_id, name, full_path, visibility, payload)
            values ($1, '100', 'backend', 'platform/backend', 'private', '{}'::jsonb)
            returning id
            """,
            provider_id,
        )
        repository_id = await connection.fetchval(
            """
            insert into repositories (workspace_id, provider, name, full_name, default_branch, status, payload)
            values ($1, 'gitea', 'agent-api', 'platform/backend/agent-api', 'main', 'active', '{}'::jsonb)
            returning id
            """,
            workspace_id,
        )
        connection_id = await connection.fetchval(
            """
            insert into repository_connections (
                workspace_id, repository_id, provider_id, group_id, provider_repository_id,
                name, full_name, default_branch, status, payload
            )
            values ($1, $2, $3, $4, '200', 'agent-api', 'platform/backend/agent-api', 'main', 'active', '{}'::jsonb)
            returning id
            """,
            workspace_id,
            repository_id,
            provider_id,
            group_id,
        )
        await connection.execute(
            """
            insert into repository_branches (connection_id, name, commit_sha, is_default, protected, payload)
            values ($1, 'main', 'abc123', true, true, '{}'::jsonb)
            """,
            connection_id,
        )
        await connection.execute(
            """
            insert into repository_commits (connection_id, branch_name, commit_sha, parent_shas, author_name, message, payload)
            values ($1, 'main', 'abc123', ARRAY[]::text[], 'Tester', '초기 커밋', '{}'::jsonb)
            """,
            connection_id,
        )
        return str(connection_id)
    except Exception:
        await connection.execute("delete from workspaces where id = $1", workspace_id)
        raise
    finally:
        await connection.close()


def test_repository_provider_group_connection_branch_and_commit_flow() -> None:
    asyncio.run(_cleanup_repository_rows())
    client = TestClient(app)

    try:
        connection_id = asyncio.run(_insert_repository_fixture())

        providers = client.get("/api/repository-providers", headers=_auth_headers())
        assert providers.status_code == 200
        assert any(item["provider"] == "gitea" for item in providers.json()["items"])

        groups = client.get("/api/repository-groups", headers=_auth_headers())
        assert groups.status_code == 200
        assert any(item["full_path"] == "platform/backend" for item in groups.json()["items"])

        connections = client.get("/api/repository-connections", headers=_auth_headers())
        assert connections.status_code == 200
        assert any(item["id"] == connection_id for item in connections.json()["items"])

        detail = client.get(f"/api/repository-connections/{connection_id}", headers=_auth_headers())
        assert detail.status_code == 200
        assert detail.json()["full_name"] == "platform/backend/agent-api"

        branches = client.get(
            f"/api/repository-connections/{connection_id}/branches", headers=_auth_headers()
        )
        assert branches.status_code == 200
        assert branches.json()["items"][0]["name"] == "main"

        commits = client.get(
            f"/api/repository-connections/{connection_id}/commits", headers=_auth_headers()
        )
        assert commits.status_code == 200
        assert commits.json()["items"][0]["commit_sha"] == "abc123"
    finally:
        asyncio.run(_cleanup_repository_rows())


def test_missing_repository_connection_returns_404() -> None:
    client = TestClient(app)

    response = client.get(f"/api/repository-connections/{uuid4()}", headers=_auth_headers())

    assert response.status_code == 404
