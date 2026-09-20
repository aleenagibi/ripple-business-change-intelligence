from dataclasses import dataclass

from app.engines.dense_engine import DenseResult
from app.engines.tfidf_engine import TFIDFResult


@dataclass(frozen=True)
class HybridResult:
    """A result produced by hybrid retrieval."""

    chunk_id: str
    chunk_index: int
    score: float
    content: str
    tfidf_rank: int | None
    dense_rank: int | None
    tfidf_score: float | None
    dense_score: float | None


class HybridRetrievalEngine:
    """
    Combines lexical and dense retrieval using Reciprocal Rank Fusion.

    RRF is used for ranking only. The original TF-IDF and dense
    similarity scores are preserved so downstream components can
    use them as independent relevance signals.
    """

    def __init__(
        self,
        rrf_k: int = 60,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be greater than zero."
            )

        self.rrf_k = rrf_k

    def fuse(
        self,
        tfidf_results: list[TFIDFResult],
        dense_results: list[DenseResult],
        top_k: int = 10,
    ) -> list[HybridResult]:
        """Fuse TF-IDF and dense rankings using RRF."""

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        scores: dict[str, float] = {}
        metadata: dict[str, dict] = {}

        for rank, result in enumerate(
            tfidf_results,
            start=1,
        ):
            chunk_id = result.chunk_id

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + 1.0 / (self.rrf_k + rank)
            )

            metadata.setdefault(
                chunk_id,
                {
                    "chunk_index": result.chunk_index,
                    "content": result.content,
                    "tfidf_rank": None,
                    "dense_rank": None,
                    "tfidf_score": None,
                    "dense_score": None,
                },
            )

            metadata[chunk_id]["tfidf_rank"] = rank
            metadata[chunk_id]["tfidf_score"] = float(
                result.score
            )

        for rank, result in enumerate(
            dense_results,
            start=1,
        ):
            chunk_id = result.chunk_id

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + 1.0 / (self.rrf_k + rank)
            )

            metadata.setdefault(
                chunk_id,
                {
                    "chunk_index": result.chunk_index,
                    "content": result.content,
                    "tfidf_rank": None,
                    "dense_rank": None,
                    "tfidf_score": None,
                    "dense_score": None,
                },
            )

            metadata[chunk_id]["dense_rank"] = rank
            metadata[chunk_id]["dense_score"] = float(
                result.score
            )

        ranked_chunk_ids = sorted(
            scores,
            key=lambda chunk_id: scores[chunk_id],
            reverse=True,
        )[:top_k]

        return [
            HybridResult(
                chunk_id=chunk_id,
                chunk_index=metadata[chunk_id]["chunk_index"],
                score=round(scores[chunk_id], 6),
                content=metadata[chunk_id]["content"],
                tfidf_rank=metadata[chunk_id]["tfidf_rank"],
                dense_rank=metadata[chunk_id]["dense_rank"],
                tfidf_score=metadata[chunk_id]["tfidf_score"],
                dense_score=metadata[chunk_id]["dense_score"],
            )
            for chunk_id in ranked_chunk_ids
        ]