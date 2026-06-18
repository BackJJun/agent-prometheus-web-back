import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_user_from_keycloak_claims(
    session: AsyncSession,
    claims: dict[str, Any],
) -> dict[str, Any]:
    user_id = str(claims["sub"])
    issuer = str(claims["iss"])
    email = claims.get("email") or claims.get("preferred_username")
    preferred_username = claims.get("preferred_username")
    name = claims.get("name") or preferred_username or email or user_id
    email_verified = claims.get("email_verified")

    payload = json.dumps(
        {
            "keycloak": {
                "azp": claims.get("azp"),
                "realm_access": claims.get("realm_access"),
                "resource_access": claims.get("resource_access"),
            }
        }
    )
    claims_payload = json.dumps(
        {
            "preferred_username": preferred_username,
            "name": claims.get("name"),
            "azp": claims.get("azp"),
        }
    )

    async with session.begin():
        await session.execute(
            text(
                """
                insert into users (id, email, name, status, last_login_at, payload)
                values (:id, :email, :name, 'active', now(), cast(:payload as jsonb))
                on conflict (id) do update set
                    email = excluded.email,
                    name = excluded.name,
                    status = 'active',
                    last_login_at = now(),
                    payload = excluded.payload,
                    updated_at = now()
                """
            ),
            {"id": user_id, "email": email, "name": name, "payload": payload},
        )
        await session.execute(
            text(
                """
                insert into user_auth_identities (
                    user_id,
                    provider,
                    issuer,
                    subject,
                    preferred_username,
                    email,
                    email_verified,
                    claims,
                    last_seen_at
                )
                values (
                    :user_id,
                    'keycloak',
                    :issuer,
                    :subject,
                    :preferred_username,
                    :email,
                    :email_verified,
                    cast(:claims as jsonb),
                    now()
                )
                on conflict (provider, issuer, subject) do update set
                    user_id = excluded.user_id,
                    preferred_username = excluded.preferred_username,
                    email = excluded.email,
                    email_verified = excluded.email_verified,
                    claims = excluded.claims,
                    last_seen_at = now(),
                    updated_at = now()
                """
            ),
            {
                "user_id": user_id,
                "issuer": issuer,
                "subject": user_id,
                "preferred_username": preferred_username,
                "email": email,
                "email_verified": email_verified,
                "claims": claims_payload,
            },
        )

    return {
        "id": user_id,
        "email": email,
        "name": name,
        "preferred_username": preferred_username,
        "auth": {
            "provider": "keycloak",
            "issuer": issuer,
            "subject": user_id,
        },
    }
