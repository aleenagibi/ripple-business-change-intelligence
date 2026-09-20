from dataclasses import dataclass

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class DenseResult:
    """A ranked dense semantic retrieval result."""

    chunk_id: str
    chunk_index: int
    score: float
    content: str


class DenseRetrievalEngine:
    """
    Dense semantic retrieval using Sentence Transformers and FAISS.

    Chunks are converted into normalized embeddings and indexed using
    FAISS inner-product search, which is equivalent to cosine similarity
    for normalized vectors.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.model = SentenceTransformer(model_name)

        self.index: faiss.Index | None = None
        self._chunks: list[dict] = []

    def build_index(
        self,
        chunks: list[dict],
    ) -> None:
        """Build a FAISS index from document chunks."""

        if not chunks:
            raise ValueError(
                "Cannot build a dense index without chunks."
            )

        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        embeddings = embeddings.astype(
            np.float32
        )

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.index.add(embeddings)

        self._chunks = chunks.copy()

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[DenseResult]:
        """Return the most semantically similar chunks."""

        if self.index is None:
            raise RuntimeError(
                "Dense retrieval index has not been built."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Search query cannot be empty."
            )

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        query_embedding = query_embedding.astype(
            np.float32
        )

        actual_k = min(
            top_k,
            len(self._chunks),
        )

        scores, indices = self.index.search(
            query_embedding,
            actual_k,
        )

        results: list[DenseResult] = []

        for score, index in zip(
            scores[0],
            indices[0],
        ):
            if index < 0:
                continue

            chunk = self._chunks[index]

            results.append(
                DenseResult(
                    chunk_id=str(chunk["id"]),
                    chunk_index=chunk["chunk_index"],
                    score=float(score),
                    content=chunk["content"],
                )
            )

        return results