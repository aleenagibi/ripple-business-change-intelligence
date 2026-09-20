from uuid import UUID

from sqlalchemy import delete

from app.db.database import SessionLocal
from app.models.canonical_entity import CanonicalEntity
from app.models.document import Document
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship
from app.models.chunk import DocumentChunk


ORGANIZATION_ID = UUID(
    "b5154ce1-c734-489e-a769-880535ceebcd"
)


def main() -> None:
    db = SessionLocal()

    try:
        chunk_ids = db.scalars(
            DocumentChunk.__table__.select()
            .with_only_columns(DocumentChunk.id)
            .join(
                Document,
                DocumentChunk.document_id == Document.id,
            )
            .where(
                Document.organization_id == ORGANIZATION_ID
            )
        ).all()

        if chunk_ids:
            db.execute(
                delete(EntityRelationship).where(
                    EntityRelationship.evidence_chunk_id.in_(chunk_ids)
                )
            )

            db.execute(
                delete(BusinessEntity).where(
                    BusinessEntity.chunk_id.in_(chunk_ids)
                )
            )

            db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.id.in_(chunk_ids)
                )
            )

        db.execute(
            delete(Document).where(
                Document.organization_id == ORGANIZATION_ID
            )
        )

        db.execute(
            delete(CanonicalEntity).where(
                CanonicalEntity.organization_id == ORGANIZATION_ID
            )
        )

        db.commit()

        print("=" * 60)
        print("RIPPLE TEST DATA CLEANUP")
        print("=" * 60)
        print(f"Organization: {ORGANIZATION_ID}")
        print("Old test corpus data removed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()