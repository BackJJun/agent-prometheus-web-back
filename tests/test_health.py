from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "prometheus-web-backend",
        "version": "0.1.0",
    }


def test_local_frontend_origin_is_allowed_by_default() -> None:
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_lan_frontend_origin_is_allowed_by_default() -> None:
    client = TestClient(app)

    response = client.options(
        "/api/settings/llm-providers",
        headers={
            "Origin": "http://192.168.14.171:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://192.168.14.171:5173"
