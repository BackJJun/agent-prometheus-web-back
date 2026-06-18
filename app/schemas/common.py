from pydantic import BaseModel


class AuthIdentityResponse(BaseModel):
    issuer: str
    subject: str
    provider: str = "keycloak"


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None = None
    name: str
    preferred_username: str | None = None
    auth: AuthIdentityResponse
