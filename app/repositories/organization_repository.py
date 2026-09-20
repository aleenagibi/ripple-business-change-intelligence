from uuid import UUID

from app.models.organization import Organization
from sqlalchemy import select
from sqlalchemy.orm import Session


class OrganizationRepository:
    """Database access layer for organizations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        statement = select(Organization).where(
            Organization.id == organization_id
        )

        return self.db.scalar(statement)

    def get_by_slug(self, slug: str) -> Organization | None:
        statement = select(Organization).where(
            Organization.slug == slug
        )

        return self.db.scalar(statement)

    def list_all(self) -> list[Organization]:
        statement = (
            select(Organization)
            .order_by(Organization.created_at.desc())
        )

        return list(self.db.scalars(statement).all())

    def add(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()

        return organization