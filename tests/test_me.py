import asyncio
import base64
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import asyncpg
import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.core.keycloak import KeycloakTokenVerifier, TokenVerificationError
from app.main import app


def _decode_jwt_payload(token: str) -> dict[str, object]:
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))


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


async def _fetch_user_id(user_id: str) -> str | None:
    connection = await asyncpg.connect(
        user="crux",
        password="crux5748#@12",
        database="agent_pmts",
        host="localhost",
        port=5432,
    )
    try:
        return await connection.fetchval("select id::text from users where id = $1", user_id)
    finally:
        await connection.close()


def test_me_maps_keycloak_user_id_to_internal_user_id() -> None:
    token = _get_keycloak_access_token()
    payload = _decode_jwt_payload(token)
    client = TestClient(app)

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == payload["sub"]
    assert body["email"] == "admin"
    assert body["auth"]["issuer"] == "http://localhost:18080/realms/agent-pmts"
    assert body["auth"]["subject"] == payload["sub"]
    assert asyncio.run(_fetch_user_id(str(payload["sub"]))) == payload["sub"]


def test_me_rejects_invalid_token() -> None:
    client = TestClient(app)

    response = client.get("/api/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def _build_test_token(
    *, audience: str | None, expires_delta: timedelta
) -> tuple[str, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = "test-key"
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "iss": "http://issuer.example/realms/test",
        "sub": "00000000-0000-0000-0000-000000000001",
        "iat": now,
        "exp": now + expires_delta,
    }
    if audience is not None:
        claims["aud"] = audience
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})
    return token, {"keys": [public_jwk]}


@pytest.mark.parametrize(
    ("audience", "expires_delta"),
    [
        (None, timedelta(minutes=5)),
        ("agent-pmts-api", timedelta(minutes=-5)),
    ],
)
def test_keycloak_verifier_rejects_missing_audience_or_expired_token(
    monkeypatch,
    audience: str | None,
    expires_delta: timedelta,
) -> None:
    token, jwks = _build_test_token(audience=audience, expires_delta=expires_delta)
    verifier = KeycloakTokenVerifier()

    async def fake_jwks() -> dict[str, object]:
        return jwks

    monkeypatch.setattr(verifier, "_get_jwks", fake_jwks)
    monkeypatch.setattr(
        "app.core.keycloak.get_settings",
        lambda: SimpleNamespace(
            keycloak_issuer="http://issuer.example/realms/test",
            keycloak_audience="agent-pmts-api",
            keycloak_jwks_url="unused",
        ),
    )

    with pytest.raises(TokenVerificationError):
        asyncio.run(verifier.verify(token))
