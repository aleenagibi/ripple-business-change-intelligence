from app.engines.nlp_engine import NLPEngine
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.repositories.chunk_repository import ChunkRepository
from app.services.entity_service import EntityService
from sqlalchemy.orm import Session


class ChunkService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ChunkRepository(db)
        self.nlp_engine = NLPEngine()

    def process_document(
        self,
        document: Document,
    ) -> list[DocumentChunk]:

        if not document.extracted_text:
            raise ValueError(
                "Document has no extracted text."
            )

        self.repository.delete_for_document(
            document.id
        )

        raw_chunks = self.nlp_engine.chunk(
            document.extracted_text
        )

        if not raw_chunks:
            raise ValueError(
                "No chunks could be generated from the document."
            )

        chunks: list[DocumentChunk] = []

        for index, content in enumerate(raw_chunks):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=content,
                token_count=self.nlp_engine.token_count(
                    content
                ),
            )

            chunks.append(chunk)

        self.repository.add_many(chunks)

        self.db.flush()

        entity_service = EntityService(self.db)

        for chunk in chunks:
            entity_service.process_chunk(chunk)

        return chunks

    def process_document(
        self,
        document: Document,
    ) -> list[DocumentChunk]:

        if not document.extracted_text:
            raise ValueError(
                "Document has no extracted text."
            )

        self.repository.delete_for_document(
            document.id
        )

        raw_chunks = self.nlp_engine.chunk(
            document.extracted_text
        )

        if not raw_chunks:
            raise ValueError(
                "No chunks could be generated from the document."
            )

        chunks: list[DocumentChunk] = []

        for index, content in enumerate(raw_chunks):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=content,
                token_count=self.nlp_engine.token_count(
                    content
                ),
            )

            chunks.append(chunk)

        self.repository.add_many(chunks)

        self.db.flush()

        for chunk in chunks:
            self.entity_service.process_chunk(
                chunk
            )

        return chunks