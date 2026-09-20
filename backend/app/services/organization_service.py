from uuid import UUID

from app.models.organization import Organization
from app.repositories.organization_repository import (
    OrganizationRepository,
)
from app.schemas.organization import OrganizationCreate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class OrganizationService:
    """Business logic for organization management."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrganizationRepository(db)

    def create(
        self,
        data: OrganizationCreate,
    ) -> Organization:

        existing = self.repository.get_by_slug(data.slug)

        if existing is not None:
            raise ValueError(
                f"Organization with slug '{data.slug}' already exists."
            )

        organization = Organization(
            name=data.name,
            slug=data.slug,
        )

        try:
            self.repository.add(organization)
            self.db.commit()
            self.db.refresh(organization)

        except IntegrityError:
            self.db.rollback()

            raise ValueError(
                f"Organization with slug '{data.slug}' already exists."
            )

        return organization

    def get_by_id(
        self,
        organization_id: UUID,
    ) -> Organization | None:

        return self.repository.get_by_id(organization_id)

    def list_all(self) -> list[Organization]:

        return self.repository.list_all()