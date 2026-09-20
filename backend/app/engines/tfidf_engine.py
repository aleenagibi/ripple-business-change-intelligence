from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class TFIDFResult:
    """A ranked TF-IDF retrieval result."""

    chunk_id: str
    chunk_index: int
    score: float
    content: str


class TFIDFEngine:
    """
    Sparse lexical retrieval using TF-IDF and cosine similarity.

    The engine is intentionally independent of the database layer.
    It receives chunk text and returns ranked retrieval results.
    """

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
        )

        self._matrix = None
        self._chunks: list[dict] = []

    def build_index(
        self,
        chunks: list[dict],
    ) -> None:
        """
        Build a TF-IDF matrix from document chunks.

        Each chunk dictionary must contain:
        - id
        - chunk_index
        - content
        """

        if not chunks:
            raise ValueError(
                "Cannot build a TF-IDF index without chunks."
            )

        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        self._matrix = self.vectorizer.fit_transform(texts)
        self._chunks = chunks.copy()

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[TFIDFResult]:
        """Return the most relevant chunks for a query."""

        if self._matrix is None:
            raise RuntimeError(
                "TF-IDF index has not been built."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Search query cannot be empty."
            )

        query_vector = self.vectorizer.transform([query])

        scores = cosine_similarity(
            query_vector,
            self._matrix,
        ).ravel()

        ranked_indices = np.argsort(
            scores
        )[::-1][:top_k]

        results: list[TFIDFResult] = []

        for index in ranked_indices:
            score = float(scores[index])

            if score <= 0:
                continue

            chunk = self._chunks[index]

            results.append(
                TFIDFResult(
                    chunk_id=str(chunk["id"]),
                    chunk_index=chunk["chunk_index"],
                    score=score,
                    content=chunk["content"],
                )
            )

        return results