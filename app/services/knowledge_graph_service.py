from uuid import UUID

import networkx as nx
from app.engines.knowledge_graph_engine import (
    GraphEdge,
    KnowledgeGraphEngine,
)
from app.repositories.canonical_entity_repository import (
    CanonicalEntityRepository,
)
from app.repositories.relationship_repository import (
    RelationshipRepository,
)
from sqlalchemy.orm import Session


class KnowledgeGraphService:
    """
    Builds an organization's canonical knowledge graph.

    Database relationships are stored between BusinessEntity mentions.
    The service resolves those mentions to CanonicalEntity identities
    before passing graph data to the database-independent graph engine.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

        self.canonical_entity_repository = (
            CanonicalEntityRepository(db)
        )

        self.relationship_repository = (
            RelationshipRepository(db)
        )

        self.engine = KnowledgeGraphEngine()

    def build_for_organization(
        self,
        organization_id: UUID,
    ) -> nx.MultiDiGraph:
        """Build the organization's canonical knowledge graph."""

        entities = (
            self.canonical_entity_repository.list_for_organization(
                organization_id
            )
        )

        relationships = (
            self.relationship_repository.list_for_organization(
                organization_id
            )
        )

        graph_edges = self._resolve_graph_edges(
            relationships
        )

        return self.engine.build(
            entities=entities,
            relationships=graph_edges,
        )

    @staticmethod
    def _resolve_graph_edges(
        relationships,
    ) -> list[GraphEdge]:
        """Resolve mention-level relationships to canonical entities."""

        resolved: dict[
            tuple[UUID, UUID, str],
            GraphEdge,
        ] = {}

        for relationship in relationships:
            source = relationship.source_entity
            target = relationship.target_entity

            if source is None or target is None:
                continue

            source_canonical = source.canonical_entity
            target_canonical = target.canonical_entity

            if (
                source_canonical is None
                or target_canonical is None
            ):
                continue

            source_id = source_canonical.id
            target_id = target_canonical.id

            if source_id == target_id:
                continue

            edge = GraphEdge(
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=relationship.relationship_type,
                confidence=relationship.confidence,
                evidence=relationship.evidence,
            )

            key = (
                source_id,
                target_id,
                relationship.relationship_type,
            )

            existing = resolved.get(key)

            if (
                existing is None
                or edge.confidence > existing.confidence
            ):
                resolved[key] = edge

        return list(resolved.values())