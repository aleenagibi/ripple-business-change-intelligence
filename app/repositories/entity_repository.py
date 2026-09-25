from uuid import UUID

from app.models.canonical_entity import CanonicalEntity
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.entity import BusinessEntity
from sqlalchemy import select
from sqlalchemy.orm import Session


class EntityRepository:
    """Database access layer for business entities and canonical entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def delete_for_chunk(
        self,
        chunk_id: UUID,
    ) -> None:
        entities = self.db.scalars(
            select(BusinessEntity).where(
                BusinessEntity.chunk_id == chunk_id
            )
        ).all()

        for entity in entities:
            self.db.delete(entity)

    def add_many(
        self,
        entities: list[BusinessEntity],
    ) -> None:
        if entities:
            self.db.add_all(entities)

    def list_for_chunk(
        self,
        chunk_id: UUID,
    ) -> list[BusinessEntity]:
        statement = (
            select(BusinessEntity)
            .where(
                BusinessEntity.chunk_id == chunk_id
            )
            .order_by(BusinessEntity.name)
        )

    

        return list(
            self.db.scalars(statement).all()
        )

    def get_canonical_entity(
        self,
        organization_id: UUID,
        normalized_name: str,
        entity_type: str,
    ) -> CanonicalEntity | None:
        statement = (
            select(CanonicalEntity)
            .where(
                CanonicalEntity.organization_id == organization_id,
                CanonicalEntity.normalized_name == normalized_name,
                CanonicalEntity.entity_type == entity_type,
            )
        )

        return self.db.scalar(statement)


    def list_canonical_entities(
        self,
        organization_id: UUID,
    ) -> list[CanonicalEntity]:
        """Return all canonical entities belonging to an organization."""

        statement = (
            select(CanonicalEntity)
            .where(
                CanonicalEntity.organization_id == organization_id
            )
            .order_by(
                CanonicalEntity.entity_type,
                CanonicalEntity.normalized_name,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )
    def add_canonical_entity(
        self,
        entity: CanonicalEntity,
    ) -> CanonicalEntity:
        self.db.add(entity)
        return entity

    def list_chunks_for_organization(
        self,
        organization_id: UUID,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(
                Document.organization_id == organization_id
            )
            .order_by(
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )
    def list_mentions_for_canonical_entity(
        self,
        canonical_entity_id: UUID,
    ) -> list[BusinessEntity]:
        """Return all document mentions belonging to a canonical entity."""

        statement = (
            select(BusinessEntity)
            .where(
                BusinessEntity.canonical_entity_id
                == canonical_entity_id
            )
            .order_by(
                BusinessEntity.created_at,
                BusinessEntity.id,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )


    def list_source_documents_for_canonical_entity(
        self,
        canonical_entity_id: UUID,
    ) -> list[tuple[UUID, str]]:
        """Return unique source documents containing a canonical entity."""

        statement = (
            select(
                Document.id,
                Document.filename,
            )
            .join(
                DocumentChunk,
                DocumentChunk.document_id == Document.id,
            )
            .join(
                BusinessEntity,
                BusinessEntity.chunk_id == DocumentChunk.id,
            )
            .where(
                BusinessEntity.canonical_entity_id
                == canonical_entity_id
            )
            .distinct()
            .order_by(
                Document.filename,
            )
        )

        return list(
            self.db.execute(statement).all()
        )

    def count_mentions_for_canonical_entity(
        self,
        canonical_entity_id: UUID,
    ) -> int:
        """Return the number of mentions assigned to a canonical entity."""

        statement = select(BusinessEntity.id).where(
            BusinessEntity.canonical_entity_id
            == canonical_entity_id
        )

        return len(
            self.db.scalars(statement).all()
        )
