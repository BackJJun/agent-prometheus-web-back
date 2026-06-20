import httpx
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app


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


def test_dashboard_summary_returns_product_shape() -> None:
    token = _get_keycloak_access_token()
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert set(body["counts"]) == {
        "web_chats",
        "plugin_tasks",
        "general_docs_indexed",
        "code_docs_indexed",
        "repository_connections",
    }
    assert all(isinstance(value, int) and value >= 0 for value in body["counts"].values())
    assert isinstance(body["recent_plugin_failures"], list)
    assert isinstance(body["recent_document_jobs"], list)
    assert isinstance(body["recent_commits"], list)


def test_dashboard_summary_returns_503_when_query_fails(monkeypatch) -> None:
    async def fail_summary() -> dict[str, object]:
        raise SQLAlchemyError("query failed")

    token = _get_keycloak_access_token()
    monkeypatch.setattr("app.api.routes.dashboard.fetch_dashboard_summary", fail_summary)
    client = TestClient(app)

    response = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Dashboard summary query failed"}
