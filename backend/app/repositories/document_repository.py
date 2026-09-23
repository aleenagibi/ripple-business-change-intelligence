from uuid import UUID

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session


class DocumentRepository:
    """Database access layer for documents."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(
        self,
        document_id: UUID,
        organization_id: UUID,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )

        return self.db.scalar(statement)

    def list_by_organization(
        self,
        organization_id: UUID,
    ) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.organization_id == organization_id)
            .order_by(Document.created_at.desc())
        )

        return list(self.db.scalars(statement).all())

    def add(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()

        return document

    def get_index_stats(
        self,
        document_id: UUID,
        organization_id: UUID,
    ) -> dict[str, int]:
        """Return derived Ripple indexing statistics for a document."""

        chunk_count_statement = (
            select(func.count(DocumentChunk.id))
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(
                DocumentChunk.document_id == document_id,
                Document.organization_id == organization_id,
            )
        )

        chunk_count = int(
            self.db.scalar(chunk_count_statement) or 0
        )

        entity_count_statement = (
            select(func.count(distinct(BusinessEntity.id)))
            .join(
                DocumentChunk,
                DocumentChunk.id == BusinessEntity.chunk_id,
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(
                DocumentChunk.document_id == document_id,
                Document.organization_id == organization_id,
            )
        )

        entity_count = int(
            self.db.scalar(entity_count_statement) or 0
        )

        relationship_count_statement = (
            select(func.count(distinct(EntityRelationship.id)))
            .join(
                DocumentChunk,
                DocumentChunk.id == EntityRelationship.evidence_chunk_id,
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(
                DocumentChunk.document_id == document_id,
                Document.organization_id == organization_id,
            )
        )

        relationship_count = int(
            self.db.scalar(relationship_count_statement) or 0
        )

        return {
            "chunk_count": chunk_count,
            "entity_count": entity_count,
            "relationship_count": relationship_count,
        }