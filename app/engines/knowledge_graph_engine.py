from dataclasses import dataclass
from uuid import UUID

import networkx as nx
from app.models.canonical_entity import CanonicalEntity


@dataclass(frozen=True)
class GraphNode:
    """Represents a canonical business entity in the knowledge graph."""

    entity_id: UUID
    name: str
    entity_type: str


@dataclass(frozen=True)
class GraphEdge:
    """Represents a relationship between canonical business entities."""

    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    confidence: float
    evidence: str


class KnowledgeGraphEngine:
    """
    Builds and queries Ripple's organizational knowledge graph.

    The engine is independent of the database and operates on canonical
    graph nodes and graph-specific edges supplied by the service layer.
    """

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def build(
        self,
        entities: list[CanonicalEntity],
        relationships: list[GraphEdge],
    ) -> nx.MultiDiGraph:
        """
        Build a canonical knowledge graph.

        Existing graph state is replaced so that the engine represents
        exactly the supplied organizational knowledge.
        """

        self.graph.clear()

        for entity in entities:
            self.add_entity(entity)

        for relationship in relationships:
            self.add_relationship(relationship)

        return self.graph

    def add_entity(
        self,
        entity: CanonicalEntity,
    ) -> None:
        """Add a canonical business entity as a graph node."""

        self.graph.add_node(
            entity.id,
            name=entity.name,
            normalized_name=entity.normalized_name,
            entity_type=entity.entity_type,
            description=entity.description,
        )

    def add_relationship(
        self,
        relationship: GraphEdge,
    ) -> None:
        """Add a graph edge when both canonical endpoints exist."""

        if (
            relationship.source_entity_id not in self.graph
            or relationship.target_entity_id not in self.graph
        ):
            return

        self.graph.add_edge(
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship_type=relationship.relationship_type,
            confidence=relationship.confidence,
            evidence=relationship.evidence,
        )

    def get_entity(
        self,
        entity_id: UUID,
    ) -> GraphNode | None:
        """Return a graph node by canonical entity ID."""

        if entity_id not in self.graph:
            return None

        node = self.graph.nodes[entity_id]

        return GraphNode(
            entity_id=entity_id,
            name=node["name"],
            entity_type=node["entity_type"],
        )

    def get_direct_neighbors(
        self,
        entity_id: UUID,
    ) -> list[GraphNode]:
        """Return entities directly connected to an entity."""

        if entity_id not in self.graph:
            return []

        neighbors: set[UUID] = set()

        neighbors.update(
            self.graph.successors(entity_id)
        )

        neighbors.update(
            self.graph.predecessors(entity_id)
        )

        result: list[GraphNode] = []

        for neighbor_id in neighbors:
            node = self.get_entity(neighbor_id)

            if node is not None:
                result.append(node)

        return sorted(
            result,
            key=lambda node: node.name.lower(),
        )

    def get_relationships(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
    ) -> list[GraphEdge]:
        """Return all relationships between two canonical entities."""

        if not self.graph.has_edge(
            source_entity_id,
            target_entity_id,
        ):
            return []

        edges = self.graph.get_edge_data(
            source_entity_id,
            target_entity_id,
        )

        if edges is None:
            return []

        return [
            GraphEdge(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=data["relationship_type"],
                confidence=data["confidence"],
                evidence=data["evidence"],
            )
            for data in edges.values()
        ]

    def shortest_path(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
    ) -> list[UUID]:
        """
        Return the shortest structural path between two entities.

        The graph is treated as undirected for path discovery because
        business impact can propagate through both incoming and
        outgoing relationships.
        """

        if (
            source_entity_id not in self.graph
            or target_entity_id not in self.graph
        ):
            return []

        try:
            return nx.shortest_path(
                self.graph.to_undirected(),
                source=source_entity_id,
                target=target_entity_id,
            )
        except nx.NetworkXNoPath:
            return []

    def get_entities_within_distance(
        self,
        entity_id: UUID,
        max_distance: int,
    ) -> list[GraphNode]:
        """
        Return entities reachable within a maximum graph distance.

        The starting entity itself is excluded from the result.
        """

        if (
            entity_id not in self.graph
            or max_distance < 1
        ):
            return []

        undirected_graph = self.graph.to_undirected()

        distances = nx.single_source_shortest_path_length(
            undirected_graph,
            entity_id,
            cutoff=max_distance,
        )

        result: list[GraphNode] = []

        for node_id in distances:
            if node_id == entity_id:
                continue

            node = self.get_entity(node_id)

            if node is not None:
                result.append(node)

        return sorted(
            result,
            key=lambda node: node.name.lower(),
        )

    def node_count(self) -> int:
        """Return the number of entities in the graph."""

        return self.graph.number_of_nodes()

    def edge_count(self) -> int:
        """Return the number of relationships in the graph."""

        return self.graph.number_of_edges()