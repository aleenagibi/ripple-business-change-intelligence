from uuid import UUID

from app.models.chunk import DocumentChunk
from app.models.document import Document
from sqlalchemy import select
from sqlalchemy.orm import Session


class ChunkRepository:
    """Database access layer for document chunks."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def delete_for_document(
        self,
        document_id: UUID,
    ) -> None:
        chunks = self.db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        ).all()

        for chunk in chunks:
            self.db.delete(chunk)

    def add_many(
        self,
        chunks: list[DocumentChunk],
    ) -> None:
        self.db.add_all(chunks)

    def list_for_document(
        self,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id
            )
            .order_by(DocumentChunk.chunk_index)
        )

        return list(
            self.db.scalars(statement).all()
        )

    def list_for_organization(
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