from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from app.core.config import settings
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plaintext password using the configured password hasher."""

    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    """Verify a plaintext password against its stored hash."""

    return password_hash.verify(
        password,
        hashed_password,
    )


def create_access_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    role: str,
) -> str:
    """Create a signed JWT access token."""

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    payload = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "role": role,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""

    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )