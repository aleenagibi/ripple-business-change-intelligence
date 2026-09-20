import asyncio
from pathlib import Path
from uuid import UUID

from app.db.database import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship
from app.services.document_service import DocumentService
from app.services.entity_service import EntityService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.relationship_service import RelationshipService
from fastapi import UploadFile
from sqlalchemy import select

ORGANIZATION_ID = UUID(
    "b5154ce1-c734-489e-a769-880535ceebcd"
)

CORPUS_DIRECTORY = (
    Path(__file__).parent
    / "data"
    / "ripple_test_corpus"
)


async def upload_document(
    document_service: DocumentService,
    file_path: Path,
) -> Document:
    """Upload one corpus document through the real document service."""

    mime_types = {
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".docx": (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    }

    content_type = mime_types.get(
        file_path.suffix.lower()
    )

    if content_type is None:
        raise ValueError(
            f"Unsupported test file type: {file_path.suffix}"
        )

    with file_path.open("rb") as file:
        upload = UploadFile(
            filename=file_path.name,
            file=file,
            headers={
                "content-type": content_type,
            },
        )

        return await document_service.upload(
            organization_id=ORGANIZATION_ID,
            upload=upload,
        )

async def main() -> None:
    print("=" * 60)
    print("RIPPLE TEST CORPUS INGESTION")
    print("=" * 60)

    if not CORPUS_DIRECTORY.exists():
        raise FileNotFoundError(
            f"Corpus directory not found: {CORPUS_DIRECTORY}"
        )

    files = sorted(
        CORPUS_DIRECTORY.glob("*.txt")
    )

    if not files:
        raise FileNotFoundError(
            f"No .txt files found in {CORPUS_DIRECTORY}"
        )

    print(f"ORGANIZATION: {ORGANIZATION_ID}")
    print(f"CORPUS FILES: {len(files)}")
    print()

    db = SessionLocal()

    try:
        document_service = DocumentService(db)

        print("UPLOADING DOCUMENTS")
        print("-" * 60)

        uploaded_documents: list[Document] = []

        for file_path in files:
            print(f"Uploading: {file_path.name}")

            document = await upload_document(
                document_service,
                file_path,
            )

            uploaded_documents.append(document)

            print(
                f"  ID: {document.id}"
            )

            print(
                f"  STATUS: {document.processing_status}"
            )

        print()
        print("=" * 60)
        print("DOCUMENT INGESTION COMPLETE")
        print("=" * 60)

        documents = db.scalars(
            select(Document)
            .where(
                Document.organization_id
                == ORGANIZATION_ID
            )
        ).all()

        chunks = db.scalars(
            select(DocumentChunk)
            .join(
                Document,
                Document.id
                == DocumentChunk.document_id,
            )
            .where(
                Document.organization_id
                == ORGANIZATION_ID
            )
        ).all()

        print(f"DOCUMENTS IN DATABASE: {len(documents)}")
        print(f"CHUNKS IN DATABASE: {len(chunks)}")
        print()

        print("=" * 60)
        print("ENTITY EXTRACTION")
        print("=" * 60)

        entity_service = EntityService(db)

        entity_service.process_organization(
            ORGANIZATION_ID
        )

        db.commit()

        entities = db.scalars(
            select(BusinessEntity)
            .join(
                DocumentChunk,
                BusinessEntity.chunk_id
                == DocumentChunk.id,
            )
            .join(
                Document,
                Document.id
                == DocumentChunk.document_id,
            )
            .where(
                Document.organization_id
                == ORGANIZATION_ID
            )
        ).all()

        print(
            f"ENTITIES EXTRACTED: {len(entities)}"
        )

        print()

        print("=" * 60)
        print("RELATIONSHIP EXTRACTION")
        print("=" * 60)

        relationship_service = RelationshipService(db)

        relationships = (
            relationship_service.process_organization(
                ORGANIZATION_ID
            )
        )

        db.commit()

        print(
            f"RELATIONSHIPS EXTRACTED: "
            f"{len(relationships)}"
        )

        print()

        print("=" * 60)
        print("KNOWLEDGE GRAPH")
        print("=" * 60)

        graph_service = KnowledgeGraphService(db)

        graph = (
            graph_service.build_for_organization(
                ORGANIZATION_ID
            )
        )

        print(
            f"NODES: {graph.number_of_nodes()}"
        )

        print(
            f"EDGES: {graph.number_of_edges()}"
        )

        print()

        print("=" * 60)
        print("RELATIONSHIPS")
        print("=" * 60)

        stored_relationships = (
            relationship_service.get_for_organization(
                ORGANIZATION_ID
            )
        )

        for relationship in stored_relationships:
            print(
                f"{relationship.relationship_type}"
                f" | "
                f"{relationship.source_entity_id}"
                f" -> "
                f"{relationship.target_entity_id}"
            )

        print()

        print("=" * 60)
        print("RIPPLE CORPUS READY")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())