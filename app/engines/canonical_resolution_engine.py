from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class CanonicalMatch:
    """Represents a semantic match against an existing canonical entity."""

    entity_id: str
    similarity: float


class CanonicalResolutionEngine:
    """
    Resolves extracted entity mentions against existing canonical entities.

    Resolution is organization-agnostic and does not depend on
    organization-specific vocabularies or aliases.

    Resolution strategy:

        exact normalized match
                ↓
        candidate filtering by entity type
                ↓
        dense semantic similarity
                +
        lexical token overlap
                ↓
        conservative acceptance threshold

    Semantic similarity is used only when exact normalization does not
    identify an existing canonical entity.
    """

    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

    # Conservative threshold to avoid collapsing distinct concepts.
    DEFAULT_THRESHOLD = 0.82

    # Dense semantic similarity carries most of the decision.
    DENSE_WEIGHT = 0.75
    LEXICAL_WEIGHT = 0.25

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "Canonical resolution threshold must be between 0 and 1."
            )

        self.model_name = model_name
        self.threshold = threshold
        self.model = self._load_model(model_name)

    @staticmethod
    @lru_cache(maxsize=2)
    def _load_model(
        model_name: str,
    ) -> SentenceTransformer:
        """
        Load and cache the embedding model.

        EntityService instances can be created repeatedly during API
        requests, so model loading must not occur for every request.
        """

        return SentenceTransformer(model_name)

    def find_best_match(
        self,
        name: str,
        entity_type: str,
        candidates: list[object],
    ) -> CanonicalMatch | None:
        """
        Find the strongest semantically equivalent canonical entity.

        Only candidates with the same entity type are considered.
        """

        normalized_name = self._normalize(name)

        if not normalized_name:
            return None

        compatible_candidates = [
            candidate
            for candidate in candidates
            if self._normalize(
                str(candidate.entity_type)
            )
            == self._normalize(entity_type)
            and self._normalize(
                str(candidate.normalized_name)
            )
        ]

        if not compatible_candidates:
            return None

        names = [
            str(candidate.name)
            for candidate in compatible_candidates
        ]

        embeddings = self.model.encode(
            [name, *names],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        query_embedding = embeddings[0]
        candidate_embeddings = embeddings[1:]

        dense_scores = np.dot(
            candidate_embeddings,
            query_embedding,
        )

        best_index = int(
            np.argmax(dense_scores)
        )

        candidate = compatible_candidates[best_index]

        dense_similarity = self._clamp(
            float(dense_scores[best_index])
        )

        lexical_similarity = self._token_overlap(
            normalized_name,
            self._normalize(
                str(candidate.normalized_name)
            ),
        )

        combined_similarity = (
            self.DENSE_WEIGHT
            * dense_similarity
            + self.LEXICAL_WEIGHT
            * lexical_similarity
        )

        if combined_similarity < self.threshold:
            return None

        return CanonicalMatch(
            entity_id=str(candidate.id),
            similarity=round(
                combined_similarity,
                4,
            ),
        )

    @staticmethod
    def _token_overlap(
        first: str,
        second: str,
    ) -> float:
        """
        Calculate token-level Jaccard similarity.

        This provides lexical evidence alongside dense semantic
        similarity and reduces accidental semantic over-merging.
        """

        first_tokens = set(first.split())
        second_tokens = set(second.split())

        if not first_tokens or not second_tokens:
            return 0.0

        intersection = first_tokens & second_tokens
        union = first_tokens | second_tokens

        return len(intersection) / len(union)

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        return " ".join(
            value.lower().strip().split()
        )

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )