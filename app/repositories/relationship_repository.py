from uuid import UUID

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.entity_relationship import EntityRelationship
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


class RelationshipRepository:
    """Database access layer for entity relationships."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def delete_for_organization(
        self,
        organization_id: UUID,
    ) -> None:
        chunk_ids = select(
            DocumentChunk.id
        ).join(
            Document,
            Document.id == DocumentChunk.document_id,
        ).where(
            Document.organization_id == organization_id
        )

        statement = delete(
            EntityRelationship
        ).where(
            EntityRelationship.evidence_chunk_id.in_(
                chunk_ids
            )
        )

        self.db.execute(statement)

    def add_many(
        self,
        relationships: list[EntityRelationship],
    ) -> None:
        if relationships:
            self.db.add_all(relationships)

    def list_for_chunk(
        self,
        chunk_id: UUID,
    ) -> list[EntityRelationship]:
        statement = (
            select(EntityRelationship)
            .where(
                EntityRelationship.evidence_chunk_id == chunk_id
            )
            .order_by(
                EntityRelationship.relationship_type,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )

    def list_for_organization(
        self,
        organization_id: UUID,
    ) -> list[EntityRelationship]:
        """Return all entity relationships belonging to an organization."""

        statement = (
            select(EntityRelationship)
            .join(
                DocumentChunk,
                DocumentChunk.id
                == EntityRelationship.evidence_chunk_id,
            )
            .join(
                Document,
                Document.id
                == DocumentChunk.document_id,
            )
            .where(
                Document.organization_id == organization_id
            )
            .order_by(
                EntityRelationship.relationship_type,
                EntityRelationship.source_entity_id,
                EntityRelationship.target_entity_id,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )