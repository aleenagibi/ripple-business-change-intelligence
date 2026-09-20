from uuid import UUID

from app.models.canonical_entity import CanonicalEntity
from sqlalchemy import select
from sqlalchemy.orm import Session


class CanonicalEntityRepository:
    """Database access layer for canonical business entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_organization(
        self,
        organization_id: UUID,
    ) -> list[CanonicalEntity]:
        statement = (
            select(CanonicalEntity)
            .where(
                CanonicalEntity.organization_id
                == organization_id
            )
            .order_by(
                CanonicalEntity.name
            )
        )

        return list(
            self.db.scalars(statement).all()
        )