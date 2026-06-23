from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="prometheus-web-backend", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    app_env: str = Field(default="local", alias="APP_ENV")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    backend_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5176,http://127.0.0.1:5176,http://localhost:3000,http://127.0.0.1:3000",
        alias="BACKEND_CORS_ORIGINS",
    )
    backend_cors_origin_regex: str | None = Field(
        default=r"http://192\.168\.\d{1,3}\.\d{1,3}:5173",
        alias="BACKEND_CORS_ORIGIN_REGEX",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://crux:crux5748%23%4012@localhost:5432/agent_pmts",
        alias="DATABASE_URL",
    )
    keycloak_issuer: str = Field(
        default="http://localhost:18080/realms/agent-pmts",
        alias="KEYCLOAK_ISSUER",
    )
    keycloak_jwks_url: str = Field(
        default="http://localhost:18080/realms/agent-pmts/protocol/openid-connect/certs",
        alias="KEYCLOAK_JWKS_URL",
    )
    keycloak_audience: str = Field(default="agent-pmts-api", alias="KEYCLOAK_AUDIENCE")
    keycloak_frontend_client_id: str = Field(
        default="agent-pmts-web",
        alias="KEYCLOAK_FRONTEND_CLIENT_ID",
    )

    bridge_base_url: str | None = Field(default="http://localhost:12345", alias="BRIDGE_BASE_URL")
    bridge_health_timeout_seconds: float = Field(default=2.0, alias="BRIDGE_HEALTH_TIMEOUT_SECONDS")
    bridge_degraded_latency_ms: int = Field(default=2000, alias="BRIDGE_DEGRADED_LATENCY_MS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

