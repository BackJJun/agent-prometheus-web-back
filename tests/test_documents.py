import asyncio
from uuid import uuid4

import asyncpg
import httpx
from fastapi.testclient import TestClient

from app.main import app

TEST_DOC_PREFIX = "pytest document"
TEST_CODE_BRANCH = "pytest-code-doc"


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


async def _cleanup_document_rows() -> None:
    connection = await _connect()
    try:
        doc_rows = await connection.fetch(
            "select id from documents where title like $1", f"{TEST_DOC_PREFIX}%"
        )
        doc_ids = [row["id"] for row in doc_rows]
        if doc_ids:
            await connection.execute(
                "delete from document_index_jobs where document_id = any($1::uuid[])", doc_ids
            )
            await connection.execute(
                "update documents set latest_version_id = null where id = any($1::uuid[])", doc_ids
            )
            await connection.execute(
                "delete from document_versions where document_id = any($1::uuid[])", doc_ids
            )
            await connection.execute("delete from documents where id = any($1::uuid[])", doc_ids)
        await connection.execute(
            "delete from code_index_jobs where branch_name = $1", TEST_CODE_BRANCH
        )
    finally:
        await connection.close()


async def _insert_code_index_job(workspace_id: str) -> None:
    connection = await _connect()
    try:
        await connection.execute(
            """
            insert into code_index_jobs (workspace_id, branch_name, status, current_step, progress, payload)
            values ($1, $2, 'completed', 'indexed', 100, '{}'::jsonb)
            """,
            workspace_id,
            TEST_CODE_BRANCH,
        )
    finally:
        await connection.close()


def test_documents_create_detail_versions_and_index_jobs() -> None:
    asyncio.run(_cleanup_document_rows())
    client = TestClient(app)
    title = f"{TEST_DOC_PREFIX} {uuid4()}"

    try:
        create_response = client.post(
            "/api/documents",
            json={
                "title": title,
                "file_name": "guide.md",
                "file_type": "markdown",
                "mime_type": "text/markdown",
                "storage_uri": "local://pytest/guide.md",
                "visibility": "workspace",
            },
            headers=_auth_headers(),
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["kind"] == "general"
        assert created["title"] == title
        assert created["indexing_status"] == "pending"

        list_response = client.get("/api/documents?kind=general", headers=_auth_headers())
        assert list_response.status_code == 200
        assert any(item["id"] == created["id"] for item in list_response.json()["items"])

        detail_response = client.get(f"/api/documents/{created['id']}", headers=_auth_headers())
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == created["id"]

        versions_response = client.get(
            f"/api/documents/{created['id']}/versions", headers=_auth_headers()
        )
        assert versions_response.status_code == 200
        assert versions_response.json()["items"][0]["version_no"] == 1

        jobs_response = client.get(
            "/api/documents/index-jobs?kind=general", headers=_auth_headers()
        )
        assert jobs_response.status_code == 200
        assert any(job["document_id"] == created["id"] for job in jobs_response.json()["items"])
    finally:
        asyncio.run(_cleanup_document_rows())


def test_code_documents_are_listed_from_code_index_jobs() -> None:
    asyncio.run(_cleanup_document_rows())
    client = TestClient(app)
    create_response = client.post(
        "/api/documents",
        json={
            "title": f"{TEST_DOC_PREFIX} workspace seed {uuid4()}",
            "file_name": "seed.md",
            "file_type": "markdown",
            "storage_uri": "local://pytest/seed.md",
            "visibility": "workspace",
        },
        headers=_auth_headers(),
    )
    workspace_id = create_response.json()["workspace_id"]

    try:
        asyncio.run(_insert_code_index_job(workspace_id))

        code_docs_response = client.get("/api/documents?kind=code", headers=_auth_headers())
        assert code_docs_response.status_code == 200
        assert any(
            item["branch_name"] == TEST_CODE_BRANCH for item in code_docs_response.json()["items"]
        )

        code_jobs_response = client.get(
            "/api/documents/index-jobs?kind=code", headers=_auth_headers()
        )
        assert code_jobs_response.status_code == 200
        assert any(
            job["branch_name"] == TEST_CODE_BRANCH for job in code_jobs_response.json()["items"]
        )
    finally:
        asyncio.run(_cleanup_document_rows())


def test_missing_document_returns_404() -> None:
    client = TestClient(app)

    response = client.get(f"/api/documents/{uuid4()}", headers=_auth_headers())

    assert response.status_code == 404
