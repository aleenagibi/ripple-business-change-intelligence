from uuid import UUID

from app.engines.dense_engine import (
    DenseResult,
    DenseRetrievalEngine,
)
from app.engines.hybrid_engine import (
    HybridResult,
    HybridRetrievalEngine,
)
from app.engines.tfidf_engine import (
    TFIDFEngine,
    TFIDFResult,
)
from app.repositories.chunk_repository import ChunkRepository
from sqlalchemy.orm import Session


class RetrievalService:
    """Coordinates retrieval across an organization's documents."""

    def __init__(self, db: Session) -> None:
        self.repository = ChunkRepository(db)

    def _get_chunks(
        self,
        organization_id: UUID,
    ) -> list[dict]:
        """Load an organization's chunks into engine-ready records."""

        chunks = self.repository.list_for_organization(
            organization_id
        )

        return [
            {
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
            }
            for chunk in chunks
        ]

    def search_tfidf(
        self,
        organization_id: UUID,
        query: str,
        top_k: int = 10,
    ) -> list[TFIDFResult]:
        """Search an organization's documents using TF-IDF."""

        chunks = self._get_chunks(
            organization_id
        )

        if not chunks:
            return []

        engine = TFIDFEngine()

        engine.build_index(chunks)

        return engine.search(
            query=query,
            top_k=top_k,
        )

    def search_dense(
        self,
        organization_id: UUID,
        query: str,
        top_k: int = 10,
    ) -> list[DenseResult]:
        """Search an organization's documents using dense retrieval."""

        chunks = self._get_chunks(
            organization_id
        )

        if not chunks:
            return []

        engine = DenseRetrievalEngine()

        engine.build_index(chunks)

        return engine.search(
            query=query,
            top_k=top_k,
        )

    def search_hybrid(
        self,
        organization_id: UUID,
        query: str,
        top_k: int = 10,
    ) -> list[HybridResult]:
        """Search using TF-IDF + dense retrieval with RRF fusion."""

        chunks = self._get_chunks(
            organization_id
        )

        if not chunks:
            return []

        retrieval_k = max(
            top_k * 2,
            20,
        )

        tfidf_engine = TFIDFEngine()
        tfidf_engine.build_index(chunks)

        tfidf_results = tfidf_engine.search(
            query=query,
            top_k=retrieval_k,
        )

        dense_engine = DenseRetrievalEngine()
        dense_engine.build_index(chunks)

        dense_results = dense_engine.search(
            query=query,
            top_k=retrieval_k,
        )

        hybrid_engine = HybridRetrievalEngine()

        return hybrid_engine.fuse(
            tfidf_results=tfidf_results,
            dense_results=dense_results,
            top_k=top_k,
        )