from uuid import UUID

from app.db.database import SessionLocal
from app.models.document import Document
from app.models.chunk import DocumentChunk
from sqlalchemy import select, func

ORGANIZATION_ID = UUID("b5154ce1-c734-489e-a769-880535ceebcd")

db = SessionLocal()

try:
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.organization_id == ORGANIZATION_ID)
            .order_by(Document.created_at)
        ).all()
    )

    print(f"Organization: {ORGANIZATION_ID}")
    print(f"Total documents: {len(documents)}")
    print()

    for document in documents:
        chunk_count = db.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
        )

        print(
            f"{document.filename} | "
            f"type={document.document_type} | "
            f"status={document.processing_status} | "
            f"chunks={chunk_count}"
        )

finally:
    db.close()
