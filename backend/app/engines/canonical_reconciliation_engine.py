from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


class ReconciliationRelation(StrEnum):
    """Relationship between two canonical entity names."""

    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    PREFIX_EXTENSION = "PREFIX_EXTENSION"
    SUFFIX_EXTENSION = "SUFFIX_EXTENSION"
    DESCRIPTIVE_EXTENSION = "DESCRIPTIVE_EXTENSION"
    CONTEXT_EXTENSION = "CONTEXT_EXTENSION"
    STRUCTURAL_MISMATCH = "STRUCTURAL_MISMATCH"
    REPEATED_NAME_ARTIFACT = "REPEATED_NAME_ARTIFACT"


@dataclass(frozen=True)
class ReconciliationCandidate:
    """Represents a proposed canonical-entity reconciliation."""

    source_entity_id: str
    source_name: str

    target_entity_id: str
    target_name: str

    entity_type: str

    dense_similarity: float
    lexical_similarity: float
    structural_similarity: float
    combined_similarity: float

    relationship: ReconciliationRelation
    reason: str
    confidence: str


class CanonicalReconciliationEngine:
    """
    Detect probable duplicate canonical entities.

    This engine is organization-agnostic and does not contain
    corpus-specific aliases.

    Semantic similarity alone is never sufficient for reconciliation.

    Evidence:

        1. Same entity type
        2. Dense semantic similarity
        3. Lexical token overlap
        4. Structural relationship between names
        5. Business-context modifier detection

    The engine only proposes candidates.
    It never modifies the database.
    """

    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

    DENSE_WEIGHT = 0.60
    LEXICAL_WEIGHT = 0.25
    STRUCTURAL_WEIGHT = 0.15

    DEFAULT_THRESHOLD = 0.82

    HIGH_CONFIDENCE_THRESHOLD = 0.88

    DISTINCTIVE_CONTEXT_MODIFIERS = frozenset(
        {
            "api",
            "apis",
            "architecture",
            "article",
            "articles",
            "checkout",
            "database",
            "databases",
            "documentation",
            "document",
            "documents",
            "gateway",
            "guide",
            "guides",
            "issue",
            "issues",
            "module",
            "modules",
            "policy",
            "policies",
            "request",
            "requests",
            "responsibility",
            "responsibilities",
            "rule",
            "rules",
            "service",
            "services",
            "status",
            "support",
            "team",
            "teams",
            "transaction",
            "transactions",
            "workflow",
            "workflows",
        }
    )

    DESCRIPTIVE_MODIFIERS = frozenset(
        {
            "successful",
            "successfully",
            "failed",
            "failure",
            "confirmed",
            "completed",
            "active",
            "inactive",
            "valid",
            "invalid",
            "pending",
            "current",
            "previous",
            "original",
            "new",
            "updated",
            "existing",
            "standard",
            "normal",
        }
    )

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        threshold: float = DEFAULT_THRESHOLD,
        high_confidence_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "Reconciliation threshold must be between 0 and 1."
            )

        if not 0.0 <= high_confidence_threshold <= 1.0:
            raise ValueError(
                "High-confidence threshold must be between 0 and 1."
            )

        if high_confidence_threshold < threshold:
            raise ValueError(
                "High-confidence threshold must be greater than or "
                "equal to the reconciliation threshold."
            )

        self.model_name = model_name
        self.threshold = threshold
        self.high_confidence_threshold = (
            high_confidence_threshold
        )

        self.model = self._load_model(
            model_name
        )

    @staticmethod
    @lru_cache(maxsize=2)
    def _load_model(
        model_name: str,
    ) -> SentenceTransformer:
        """
        Load and cache the embedding model.

        The model is shared between engine instances to avoid
        repeatedly loading SentenceTransformer weights.
        """

        return SentenceTransformer(
            model_name
        )

    def find_candidates(
        self,
        entities: Sequence[object],
    ) -> list[ReconciliationCandidate]:
        """
        Find probable duplicate canonical entities.

        Each entity pair is evaluated once.

        No database mutation occurs.
        """

        valid_entities = (
            self._filter_valid_entities(
                entities
            )
        )

        if len(valid_entities) < 2:
            return []

        grouped_entities = (
            self._group_by_entity_type(
                valid_entities
            )
        )

        candidates: list[
            ReconciliationCandidate
        ] = []

        for entity_type, typed_entities in (
            grouped_entities.items()
        ):
            if len(typed_entities) < 2:
                continue

            candidates.extend(
                self._find_candidates_for_type(
                    entity_type=entity_type,
                    entities=typed_entities,
                )
            )

        return sorted(
            candidates,
            key=lambda candidate: (
                -candidate.combined_similarity,
                candidate.entity_type,
                candidate.source_name.lower(),
                candidate.target_name.lower(),
            ),
        )

    def _find_candidates_for_type(
        self,
        entity_type: str,
        entities: Sequence[object],
    ) -> list[ReconciliationCandidate]:
        """Find candidates within one entity type."""

        names = [
            str(entity.name).strip()
            for entity in entities
        ]

        embeddings = self.model.encode(
            names,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        similarity_matrix = np.dot(
            embeddings,
            embeddings.T,
        )

        candidates: list[
            ReconciliationCandidate
        ] = []

        for first_index in range(
            len(entities)
        ):
            first_entity = entities[
                first_index
            ]

            for second_index in range(
                first_index + 1,
                len(entities),
            ):
                second_entity = entities[
                    second_index
                ]

                first_name = self._normalize(
                    str(
                        first_entity.normalized_name
                    )
                )

                second_name = self._normalize(
                    str(
                        second_entity.normalized_name
                    )
                )

                if first_name == second_name:
                    continue

                relationship = (
                    self._classify_relationship(
                        first_name,
                        second_name,
                    )
                )

                if (
                    relationship
                    == ReconciliationRelation.STRUCTURAL_MISMATCH
                ):
                    continue

                dense_similarity = self._clamp(
                    float(
                        similarity_matrix[
                            first_index,
                            second_index,
                        ]
                    )
                )

                lexical_similarity = (
                    self._token_similarity(
                        first_name,
                        second_name,
                    )
                )

                structural_similarity = (
                    self._structural_similarity(
                        first_name,
                        second_name,
                        relationship,
                    )
                )

                combined_similarity = (
                    self.DENSE_WEIGHT
                    * dense_similarity
                    + self.LEXICAL_WEIGHT
                    * lexical_similarity
                    + self.STRUCTURAL_WEIGHT
                    * structural_similarity
                )

                if not self._passes_threshold(
                    combined_similarity=combined_similarity,
                    dense_similarity=dense_similarity,
                    relationship=relationship,
                ):
                    continue

                reason = self._build_reason(
                    relationship
                )

                confidence = (
                    self._calculate_confidence(
                        combined_similarity=combined_similarity,
                        dense_similarity=dense_similarity,
                        relationship=relationship,
                    )
                )

                candidates.append(
                    ReconciliationCandidate(
                        source_entity_id=str(
                            first_entity.id
                        ),
                        source_name=str(
                            first_entity.name
                        ),
                        target_entity_id=str(
                            second_entity.id
                        ),
                        target_name=str(
                            second_entity.name
                        ),
                        entity_type=entity_type,
                        dense_similarity=round(
                            dense_similarity,
                            4,
                        ),
                        lexical_similarity=round(
                            lexical_similarity,
                            4,
                        ),
                        structural_similarity=round(
                            structural_similarity,
                            4,
                        ),
                        combined_similarity=round(
                            combined_similarity,
                            4,
                        ),
                        relationship=relationship,
                        reason=reason,
                        confidence=confidence,
                    )
                )

        return candidates

    @classmethod
    def _classify_relationship(
        cls,
        first: str,
        second: str,
    ) -> ReconciliationRelation:
        """
        Classify the lexical relationship between two entity names.

        The classifier distinguishes genuine descriptive/context
        extensions from extraction artifacts where an entity name
        has been repeated inside a larger phrase.
        """

        first_tokens = first.split()
        second_tokens = second.split()

        if not first_tokens or not second_tokens:
            return ReconciliationRelation.STRUCTURAL_MISMATCH

        first_set = set(first_tokens)
        second_set = set(second_tokens)

        if first_set == second_set:
            return ReconciliationRelation.EXACT_DUPLICATE

        repeated_relation = (
            cls._detect_repeated_name_artifact(
                first_tokens,
                second_tokens,
            )
        )

        if repeated_relation:
            return ReconciliationRelation.REPEATED_NAME_ARTIFACT

        if first_set.issubset(second_set):
            additional = second_set - first_set

            return cls._classify_extension(
                additional
            )

        if second_set.issubset(first_set):
            additional = first_set - second_set

            return cls._classify_extension(
                additional
            )

        return ReconciliationRelation.STRUCTURAL_MISMATCH

    @staticmethod
    def _detect_repeated_name_artifact(
        first_tokens: list[str],
        second_tokens: list[str],
    ) -> bool:
        """
        Detect repeated-name extraction artifacts.

        One entity name must occur as a contiguous token sequence
        at least twice inside the longer entity name.

        Example:

            checkout workflow

            checkout workflow the checkout workflow

        is treated as a likely extraction artifact.
        """

        if len(first_tokens) == len(second_tokens):
            return False

        shorter, longer = (
            (first_tokens, second_tokens)
            if len(first_tokens) < len(second_tokens)
            else (second_tokens, first_tokens)
        )

        window_size = len(shorter)

        if window_size == 0:
            return False

        occurrences = 0

        for index in range(
            len(longer) - window_size + 1
        ):
            window = longer[
                index : index + window_size
            ]

            if window == shorter:
                occurrences += 1

                if occurrences >= 2:
                    return True

        return False
    @classmethod
    def _classify_extension(
        cls,
        additional_tokens: set[str],
    ) -> ReconciliationRelation:    
        """
        Classify tokens added to the shorter entity name.
        """

        if not additional_tokens:
            return ReconciliationRelation.EXACT_DUPLICATE

        if (
            additional_tokens
            & cls.DISTINCTIVE_CONTEXT_MODIFIERS
        ):
            return ReconciliationRelation.CONTEXT_EXTENSION

        if (
            additional_tokens
            & cls.DESCRIPTIVE_MODIFIERS
        ):
            return ReconciliationRelation.DESCRIPTIVE_EXTENSION

        return ReconciliationRelation.DESCRIPTIVE_EXTENSION

    @classmethod
    def _structural_similarity(
        cls,
        first: str,
        second: str,
        relationship: ReconciliationRelation,
    ) -> float:
        """
        Calculate structural compatibility.

        Context extensions receive deliberately low evidence
        because they may represent narrower business concepts.

        Descriptive extensions receive stronger evidence because
        they often represent a state or qualifier of the same
        underlying concept.
        """

        if (
            relationship
            == ReconciliationRelation.EXACT_DUPLICATE
        ):
            return 1.0
        if (
            relationship
            == ReconciliationRelation.REPEATED_NAME_ARTIFACT
        ):
            return 1.0
        if (
            relationship
            == ReconciliationRelation.CONTEXT_EXTENSION
        ):
            return 0.20

        if (
            relationship
            == ReconciliationRelation.DESCRIPTIVE_EXTENSION
        ):
            return 0.90

        if (
            relationship
            == ReconciliationRelation.PREFIX_EXTENSION
        ):
            return 0.75

        if (
            relationship
            == ReconciliationRelation.SUFFIX_EXTENSION
        ):
            return 0.75

        return 0.0

    @classmethod
    def _passes_threshold(
        cls,
        combined_similarity: float,
        dense_similarity: float,
        relationship: ReconciliationRelation,
    ) -> bool:
        """
        Determine whether a pair is sufficiently similar.

        Context extensions require substantially stronger dense
        evidence and are still not eligible for HIGH confidence.
        """

        if (
            relationship
            == ReconciliationRelation.CONTEXT_EXTENSION
        ):
            return (
                dense_similarity >= 0.94
                and combined_similarity >= 0.86
            )

        return combined_similarity >= cls.DEFAULT_THRESHOLD

    @classmethod
    def _calculate_confidence(
        cls,
        combined_similarity: float,
        dense_similarity: float,
        relationship: ReconciliationRelation,
    ) -> str:
        """
        Convert evidence into an interpretable confidence level.
        """

        if (
            relationship
            == ReconciliationRelation.REPEATED_NAME_ARTIFACT
        ):
            if (
                dense_similarity >= 0.90
                and combined_similarity >= 0.85
            ):
                return "HIGH"

            return "MEDIUM"

        if (
            relationship
            == ReconciliationRelation.CONTEXT_EXTENSION
        ):
            return "REVIEW"

        if (
            dense_similarity >= 0.94
            and combined_similarity
            >= cls.HIGH_CONFIDENCE_THRESHOLD
            and relationship
            in {
                ReconciliationRelation.DESCRIPTIVE_EXTENSION,
                ReconciliationRelation.EXACT_DUPLICATE,
            }
        ):
            return "HIGH"

        if combined_similarity >= 0.85:
            return "MEDIUM"

        return "REVIEW"

    @staticmethod
    def _build_reason(
        relationship: ReconciliationRelation,
    ) -> str:
        """Build an explainable reconciliation reason."""

        reasons = {
            ReconciliationRelation.EXACT_DUPLICATE: (
                "The entities have equivalent normalized token "
                "structure and strong semantic similarity."
            ),
            ReconciliationRelation.REPEATED_NAME_ARTIFACT: (
                "One entity name is repeated inside the other name, "
                "indicating a likely extraction artifact rather than "
                "a distinct business entity."
            ),
            ReconciliationRelation.DESCRIPTIVE_EXTENSION: (
                "One name extends the other with a descriptive "
                "state or qualifier rather than a distinct "
                "business artifact."
            ),
            ReconciliationRelation.PREFIX_EXTENSION: (
                "One entity name is a structural extension of "
                "the other with compatible terminology."
            ),
            ReconciliationRelation.SUFFIX_EXTENSION: (
                "One entity name adds a compatible descriptive "
                "suffix to the other."
            ),
            ReconciliationRelation.CONTEXT_EXTENSION: (
                "One name adds a business-context or artifact "
                "modifier that may represent a narrower "
                "concept; manual review is required."
            ),
            ReconciliationRelation.STRUCTURAL_MISMATCH: (
                "The entity names do not have sufficiently "
                "compatible lexical structure."
            ),
        }

        return reasons[relationship]

    @staticmethod
    def _filter_valid_entities(
        entities: Sequence[object],
    ) -> list[object]:
        """Remove malformed canonical entities."""

        valid_entities: list[object] = []

        for entity in entities:
            entity_id = getattr(
                entity,
                "id",
                None,
            )

            name = getattr(
                entity,
                "name",
                None,
            )

            normalized_name = getattr(
                entity,
                "normalized_name",
                None,
            )

            entity_type = getattr(
                entity,
                "entity_type",
                None,
            )

            if (
                entity_id is None
                or not str(name).strip()
                or not str(normalized_name).strip()
                or not str(entity_type).strip()
            ):
                continue

            valid_entities.append(
                entity
            )

        return valid_entities

    @staticmethod
    def _group_by_entity_type(
        entities: Sequence[object],
    ) -> dict[str, list[object]]:
        """Group canonical entities by entity type."""

        grouped: dict[
            str,
            list[object],
        ] = {}

        for entity in entities:
            entity_type = str(
                entity.entity_type
            ).strip().upper()

            grouped.setdefault(
                entity_type,
                [],
            ).append(entity)

        return grouped

    @staticmethod
    def _token_similarity(
        first: str,
        second: str,
    ) -> float:
        """Calculate token-level Jaccard similarity."""

        first_tokens = set(
            first.split()
        )

        second_tokens = set(
            second.split()
        )

        if (
            not first_tokens
            or not second_tokens
        ):
            return 0.0

        intersection = (
            first_tokens
            & second_tokens
        )

        union = (
            first_tokens
            | second_tokens
        )

        return (
            len(intersection)
            / len(union)
        )

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        """Normalize whitespace and casing."""

        return " ".join(
            value.lower()
            .strip()
            .split()
        )

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        """Clamp a similarity value to [0, 1]."""

        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )