from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app


def test_database_health_reports_connected_database_and_extensions() -> None:
    client = TestClient(app)

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "agent_pmts",
        "extensions": {
            "pgcrypto": True,
            "vector": True,
        },
    }


def test_database_health_returns_503_when_database_check_fails(monkeypatch) -> None:
    async def fail_database_health() -> dict[str, object]:
        raise SQLAlchemyError("connection failed")

    monkeypatch.setattr("app.api.routes.health.fetch_database_health", fail_database_health)
    client = TestClient(app)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database health check failed"}
