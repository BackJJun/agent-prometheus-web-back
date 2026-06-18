import json
import time
from typing import Any

import httpx
import jwt
from jwt import PyJWK, PyJWTError

from app.core.config import get_settings


class TokenVerificationError(Exception):
    pass


class KeycloakTokenVerifier:
    def __init__(self) -> None:
        self._jwks: dict[str, Any] | None = None
        self._jwks_expires_at = 0.0

    async def _get_jwks(self) -> dict[str, Any]:
        now = time.time()
        if self._jwks is not None and now < self._jwks_expires_at:
            return self._jwks

        settings = get_settings()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.keycloak_jwks_url)
            response.raise_for_status()
            self._jwks = response.json()
            self._jwks_expires_at = now + 300
            return self._jwks

    async def verify(self, token: str) -> dict[str, Any]:
        settings = get_settings()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            jwks = await self._get_jwks()
            jwk = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
            if jwk is None:
                self._jwks = None
                jwks = await self._get_jwks()
                jwk = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
            if jwk is None:
                raise TokenVerificationError("Signing key not found")

            signing_key = PyJWK.from_json(json.dumps(jwk)).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=settings.keycloak_audience,
                issuer=settings.keycloak_issuer,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except (httpx.HTTPError, PyJWTError, KeyError, ValueError) as exc:
            raise TokenVerificationError("Invalid access token") from exc


keycloak_token_verifier = KeycloakTokenVerifier()
