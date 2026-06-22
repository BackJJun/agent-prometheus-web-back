from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.keycloak import (
    KeycloakTokenExchangeError,
    TokenVerificationError,
    exchange_password_for_tokens,
    exchange_refresh_token,
    keycloak_token_verifier,
)
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.services.user_service import ensure_user_from_keycloak_claims

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _build_token_response(
    token_response: dict[str, Any],
    session: AsyncSession,
) -> dict[str, Any]:
    access_token = token_response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token exchange did not return an access token",
        )

    try:
        claims = await keycloak_token_verifier.verify(access_token)
    except TokenVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    user = await ensure_user_from_keycloak_claims(session, claims)
    refresh_token = token_response.get("refresh_token")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token if isinstance(refresh_token, str) else None,
        "user": user,
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    try:
        token_response = await exchange_password_for_tokens(payload.email, payload.password)
    except KeycloakTokenExchangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc

    return await _build_token_response(token_response, session)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    try:
        token_response = await exchange_refresh_token(payload.refresh_token)
    except KeycloakTokenExchangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    return await _build_token_response(token_response, session)
