from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload used to register an organization owner."""

    organization_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    organization_slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    """Credentials used to authenticate a user."""

    email: EmailStr

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )


class OrganizationSummary(BaseModel):
    """Organization information included in authentication responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class UserSummary(BaseModel):
    """Authenticated user information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: str
    organization_id: UUID


class AuthResponse(BaseModel):
    """Authentication response containing the access token."""

    access_token: str
    token_type: str = "bearer"
    user: UserSummary
    organization: OrganizationSummary