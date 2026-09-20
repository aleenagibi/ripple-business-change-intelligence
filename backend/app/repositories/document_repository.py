from uuid import UUID

from app.models.document import Document
from sqlalchemy import select
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