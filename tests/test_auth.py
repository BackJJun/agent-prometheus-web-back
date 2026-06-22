from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


def test_auth_login_exchanges_credentials_through_backend(monkeypatch) -> None:
    calls: dict[str, object] = {}

    async def fake_exchange_password(username: str, password: str) -> dict[str, str]:
        calls["credentials"] = {"username": username, "password": password}
        return {"access_token": "access-token", "refresh_token": "refresh-token"}

    async def fake_verify(token: str) -> dict[str, str]:
        calls["verified_token"] = token
        return {
            "sub": "kc-user-id",
            "iss": "http://localhost:18080/realms/agent-pmts",
            "email": "admin",
            "preferred_username": "admin",
            "name": "Admin Prometheus",
        }

    async def fake_ensure_user(_session: object, claims: dict[str, str]) -> dict[str, object]:
        calls["claims"] = claims
        return {
            "id": claims["sub"],
            "email": claims["email"],
            "name": claims["name"],
            "preferred_username": claims["preferred_username"],
            "auth": {
                "provider": "keycloak",
                "issuer": claims["iss"],
                "subject": claims["sub"],
            },
        }

    monkeypatch.setattr("app.api.routes.auth.exchange_password_for_tokens", fake_exchange_password)
    monkeypatch.setattr(
        "app.api.routes.auth.keycloak_token_verifier",
        SimpleNamespace(verify=fake_verify),
    )
    monkeypatch.setattr("app.api.routes.auth.ensure_user_from_keycloak_claims", fake_ensure_user)

    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": "admin", "password": "12345"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token"
    assert response.json()["refresh_token"] == "refresh-token"
    assert response.json()["user"]["id"] == "kc-user-id"
    assert calls["credentials"] == {"username": "admin", "password": "12345"}
    assert calls["verified_token"] == "access-token"


def test_auth_refresh_exchanges_refresh_token_through_backend(monkeypatch) -> None:
    calls: dict[str, object] = {}

    async def fake_exchange_refresh_token(refresh_token: str) -> dict[str, str]:
        calls["refresh_token"] = refresh_token
        return {"access_token": "fresh-access", "refresh_token": "fresh-refresh"}

    async def fake_verify(token: str) -> dict[str, str]:
        calls["verified_token"] = token
        return {
            "sub": "kc-user-id",
            "iss": "http://localhost:18080/realms/agent-pmts",
            "email": "admin",
            "preferred_username": "admin",
            "name": "Admin Prometheus",
        }

    async def fake_ensure_user(_session: object, claims: dict[str, str]) -> dict[str, object]:
        calls["claims"] = claims
        return {
            "id": claims["sub"],
            "email": claims["email"],
            "name": claims["name"],
            "preferred_username": claims["preferred_username"],
            "auth": {
                "provider": "keycloak",
                "issuer": claims["iss"],
                "subject": claims["sub"],
            },
        }

    monkeypatch.setattr("app.api.routes.auth.exchange_refresh_token", fake_exchange_refresh_token)
    monkeypatch.setattr(
        "app.api.routes.auth.keycloak_token_verifier",
        SimpleNamespace(verify=fake_verify),
    )
    monkeypatch.setattr("app.api.routes.auth.ensure_user_from_keycloak_claims", fake_ensure_user)

    client = TestClient(app)
    response = client.post("/api/auth/refresh", json={"refresh_token": "old-refresh"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "fresh-access"
    assert response.json()["refresh_token"] == "fresh-refresh"
    assert response.json()["user"]["id"] == "kc-user-id"
    assert calls["refresh_token"] == "old-refresh"
    assert calls["verified_token"] == "fresh-access"

