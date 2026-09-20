from uuid import UUID

from app.models.user import User
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    """Database access layer for users."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        statement = select(User).where(
            User.id == user_id,
        )

        return self.db.scalar(statement)

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        statement = select(User).where(
            User.email == email,
        )

        return self.db.scalar(statement)

    def add(
        self,
        user: User,
    ) -> User:
        self.db.add(user)
        self.db.flush()

        return user