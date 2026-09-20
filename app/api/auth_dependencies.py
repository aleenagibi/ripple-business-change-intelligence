from uuid import UUID

import jwt
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer(
    auto_error=False,
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme,
    ),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(
            credentials.credentials,
        )

        subject = payload.get("sub")

        if not subject:
            raise ValueError("Missing token subject.")

        user_id = UUID(subject)

    except (
        jwt.InvalidTokenError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = UserRepository(db).get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_organization_access(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the authenticated user belongs to the requested organization.
    """

    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization.",
        )

    return current_user