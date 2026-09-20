from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.engines.canonical_reconciliation_engine import (
    CanonicalReconciliationEngine,
    ReconciliationCandidate,
)
from app.models.canonical_entity import CanonicalEntity
from app.repositories.entity_repository import EntityRepository


@dataclass(frozen=True)
class ReconciliationResult:
    """Result of a canonical-entity reconciliation operation."""

    source_entity_id: UUID
    source_name: str

    target_entity_id: UUID
    target_name: str

    entity_type: str

    mentions_reassigned: int

    similarity: float
    confidence: str


class CanonicalReconciliationService:
    """
    Safely reconciles duplicate canonical entities.

    Responsibilities:

        1. Detect candidate duplicate canonical entities.
        2. Validate that both entities belong to the same organization.
        3. Select a deterministic surviving canonical entity.
        4. Reassign BusinessEntity mentions.
        5. Preserve EntityRelationship rows.
        6. Remove the redundant canonical entity.
        7. Commit the complete operation atomically.

    The service never deletes documents or chunks.
    """

    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db
        self.repository = EntityRepository(db)
        self.engine = CanonicalReconciliationEngine()

    def find_candidates(
        self,
        organization_id: UUID,
    ) -> list[ReconciliationCandidate]:
        """
        Perform an inspection-only reconciliation scan.

        This method does not modify the database.
        """

        entities = self.repository.list_canonical_entities(
            organization_id
        )

        return self.engine.find_candidates(
            entities
        )

    def reconcile_candidate(
        self,
        organization_id: UUID,
        candidate: ReconciliationCandidate,
    ) -> ReconciliationResult:
        """
        Reconcile one previously identified candidate.

        The operation is transactional.

        All BusinessEntity mentions belonging to the redundant
        canonical entity are reassigned to the surviving entity
        before the redundant entity is deleted.

        EntityRelationship rows remain intact because they reference
        BusinessEntity mentions rather than CanonicalEntity records.
        """

        source_entity = self._get_canonical_entity(
            organization_id=organization_id,
            entity_id=UUID(candidate.source_entity_id),
        )

        target_entity = self._get_canonical_entity(
            organization_id=organization_id,
            entity_id=UUID(candidate.target_entity_id),
        )

        self._validate_candidate(
            source_entity=source_entity,
            target_entity=target_entity,
            candidate=candidate,
        )

        survivor, redundant = self._select_survivor(
            source_entity=source_entity,
            target_entity=target_entity,
            relationship=candidate.relationship,
        )

        mentions = (
            self.repository.list_mentions_for_canonical_entity(
                redundant.id
            )
        )

        mentions_reassigned = 0

        for mention in mentions:
            mention.canonical_entity_id = survivor.id
            mentions_reassigned += 1

        self.db.flush()

        remaining_mentions = (
            self.repository.count_mentions_for_canonical_entity(
                redundant.id
            )
        )

        if remaining_mentions != 0:
            raise RuntimeError(
                "Canonical reconciliation failed: "
                f"{remaining_mentions} BusinessEntity mentions "
                "still reference the redundant canonical entity."
            )

        self.db.delete(redundant)

        self.db.flush()

        result = ReconciliationResult(
            source_entity_id=redundant.id,
            source_name=redundant.name,
            target_entity_id=survivor.id,
            target_name=survivor.name,
            entity_type=survivor.entity_type,
            mentions_reassigned=mentions_reassigned,
            similarity=candidate.combined_similarity,
            confidence=candidate.confidence,
        )

        self.db.commit()

        return result

    def reconcile_all(
        self,
        organization_id: UUID,
        minimum_confidence: str = "HIGH",
    ) -> list[ReconciliationResult]:
        """
        Reconcile all candidates meeting the requested
        confidence threshold.

        Candidates are recalculated after every successful
        reconciliation so that no stale candidate IDs are used.
        """

        candidates = self.find_candidates(
            organization_id
        )

        confidence_order = {
            "REVIEW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        }

        minimum_level = confidence_order.get(
            minimum_confidence.upper()
        )

        if minimum_level is None:
            raise ValueError(
                f"Invalid minimum confidence: "
                f"{minimum_confidence}. "
                f"Expected one of: "
                f"{', '.join(confidence_order)}"
            )

        results: list[ReconciliationResult] = []

        while candidates:
            candidate = next(
                (
                    item
                    for item in candidates
                    if confidence_order[item.confidence]
                    >= minimum_level
                ),
                None,
            )

            if candidate is None:
                break

            try:
                result = self.reconcile_candidate(
                    organization_id=organization_id,
                    candidate=candidate,
                )
            except Exception:
                self.db.rollback()
                raise

            results.append(result)

            # Rebuild candidates after every merge.
            #
            # This is important because the canonical-entity
            # collection has changed and previous candidate IDs
            # may no longer represent the current database state.
            candidates = self.find_candidates(
                organization_id
            )

        return results

    @staticmethod
    def _select_survivor(
        source_entity: CanonicalEntity,
        target_entity: CanonicalEntity,
        relationship: str,
    ) -> tuple[CanonicalEntity, CanonicalEntity]:
        """
        Select which canonical entity survives reconciliation.

        Returns:

            (survivor, redundant_entity)

        For repeated extraction artifacts, the shorter and
        cleaner canonical name survives.

        The fallback rules are deterministic so reconciliation
        never depends on arbitrary candidate ordering.
        """

        if relationship == "REPEATED_NAME_ARTIFACT":
            source_tokens = (
                source_entity.normalized_name.split()
            )

            target_tokens = (
                target_entity.normalized_name.split()
            )

            if len(source_tokens) < len(target_tokens):
                return source_entity, target_entity

            if len(target_tokens) < len(source_tokens):
                return target_entity, source_entity

        # Prefer the shorter normalized name.
        if len(source_entity.normalized_name) < len(
            target_entity.normalized_name
        ):
            return source_entity, target_entity

        if len(target_entity.normalized_name) < len(
            source_entity.normalized_name
        ):
            return target_entity, source_entity

        # Final deterministic tie-breaker.
        if str(source_entity.id) < str(target_entity.id):
            return source_entity, target_entity

        return target_entity, source_entity

    def _get_canonical_entity(
        self,
        organization_id: UUID,
        entity_id: UUID,
    ) -> CanonicalEntity:
        """
        Retrieve a canonical entity and ensure it belongs
        to the requested organization.
        """

        entities = self.repository.list_canonical_entities(
            organization_id
        )

        entity = next(
            (
                candidate
                for candidate in entities
                if candidate.id == entity_id
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                "Canonical entity does not exist in "
                "the requested organization: "
                f"{entity_id}"
            )

        return entity

    @staticmethod
    def _validate_candidate(
        source_entity: CanonicalEntity,
        target_entity: CanonicalEntity,
        candidate: ReconciliationCandidate,
    ) -> None:
        """
        Validate that the candidate still represents a
        safe reconciliation at execution time.
        """

        if source_entity.id == target_entity.id:
            raise ValueError(
                "Source and target canonical entities "
                "must be different."
            )

        if (
            source_entity.organization_id
            != target_entity.organization_id
        ):
            raise ValueError(
                "Canonical entities from different "
                "organizations cannot be reconciled."
            )

        if (
            source_entity.entity_type.upper()
            != target_entity.entity_type.upper()
        ):
            raise ValueError(
                "Canonical entities with different "
                "entity types cannot be reconciled."
            )

        expected_ids = {
            candidate.source_entity_id,
            candidate.target_entity_id,
        }

        actual_ids = {
            str(source_entity.id),
            str(target_entity.id),
        }

        if expected_ids != actual_ids:
            raise ValueError(
                "Reconciliation candidate does not match "
                "the supplied canonical entities."
            )