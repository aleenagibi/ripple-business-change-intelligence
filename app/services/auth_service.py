from uuid import UUID

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import (
    OrganizationRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class AuthService:
    """Business logic for user registration and authentication."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)
        self.organization_repository = OrganizationRepository(db)

    def register(
        self,
        data: RegisterRequest,
    ) -> AuthResponse:
        email = str(data.email).lower().strip()

        existing_user = self.user_repository.get_by_email(
            email,
        )

        if existing_user is not None:
            raise ValueError(
                "An account with this email already exists.",
            )

        existing_organization = (
            self.organization_repository.get_by_slug(
                data.organization_slug,
            )
        )

        if existing_organization is not None:
            raise ValueError(
                "An organization with this slug already exists.",
            )

        organization = Organization(
            name=data.organization_name.strip(),
            slug=data.organization_slug,
        )

        user = User(
            email=email,
            password_hash=hash_password(data.password),
            role="owner",
        )

        organization.users.append(user)

        try:
            self.db.add(organization)
            self.db.commit()
            self.db.refresh(organization)
            self.db.refresh(user)

        except IntegrityError:
            self.db.rollback()

            raise ValueError(
                "The organization or email is already registered.",
            )

        access_token = create_access_token(
            user_id=user.id,
            organization_id=organization.id,
            role=user.role,
        )

        return AuthResponse(
            access_token=access_token,
            user=user,
            organization=organization,
        )

    def login(
        self,
        data: LoginRequest,
    ) -> AuthResponse:
        email = str(data.email).lower().strip()

        user = self.user_repository.get_by_email(
            email,
        )

        if user is None or not verify_password(
            data.password,
            user.password_hash,
        ):
            raise ValueError(
                "Invalid email or password.",
            )

        organization = user.organization

        access_token = create_access_token(
            user_id=user.id,
            organization_id=organization.id,
            role=user.role,
        )

        return AuthResponse(
            access_token=access_token,
            user=user,
            organization=organization,
        )