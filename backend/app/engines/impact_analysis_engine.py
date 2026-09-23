from dataclasses import dataclass
from uuid import UUID

import networkx as nx


@dataclass(frozen=True)
class ImpactResult:
    """Represents the calculated business impact of a business entity."""

    entity_id: UUID
    name: str
    entity_type: str
    impact_score: float
    impact_level: str
    impact_origin: str
    impact_category: str
    semantic_relevance: float
    relationship_strength: float
    graph_proximity: float
    entity_importance: float
    propagation_distance: int
    path: tuple[UUID, ...]
    explanation: str


class ImpactAnalysisEngine:
    """
    Calculates business impact using semantic evidence and
    knowledge-graph propagation.

    Direct impact is driven primarily by semantic relevance.

    Propagated impact is derived from:
        semantic relevance
        × relationship strength
        × graph-distance decay

    Graph connectivity alone must never create a high-impact result.
    """

    # Direct impact is primarily semantic.
    DIRECT_SEMANTIC_WEIGHT = 0.85
    DIRECT_IMPORTANCE_WEIGHT = 0.15

    # Propagated impact is deliberately weaker.
    PROPAGATED_SEMANTIC_WEIGHT = 0.60
    PROPAGATED_RELATIONSHIP_WEIGHT = 0.25
    # Propagated results must retain enough evidence to be
    # considered a meaningful business impact.
    # Propagated results become progressively stricter as graph
    # distance increases. This prevents weak relationships from
    # producing misleading multi-hop impacts.
    MIN_PROPAGATED_IMPACT_SCORE = 0.18

    PROPAGATION_THRESHOLDS = {
        1: {
            "semantic": 0.12,
            "relationship": 0.60,
        },
        2: {
            "semantic": 0.20,
            "relationship": 0.70,
        },
        3: {
            "semantic": 0.24,
            "relationship": 0.82,
        },
    }

    PROPAGATED_PROXIMITY_WEIGHT = 0.15

    RELATIONSHIP_STRENGTH = {
    # ---------------------------------------------------------
    # Strong technical / functional dependencies
    # ---------------------------------------------------------
    "USES": 1.00,
    "DEPENDS_ON": 1.00,
    "CALLS": 0.98,
    "READS_FROM": 0.95,
    "WRITES_TO": 0.95,
    "QUERIES": 0.95,
    "FEEDS": 0.92,
    "TRIGGERS": 0.92,
    "ROUTES_TO": 0.92,
    "IMPLEMENTS": 0.90,
    "SUPPORTS": 0.90,

    # ---------------------------------------------------------
    # Business / operational ownership
    # ---------------------------------------------------------
    "OWNED_BY": 0.88,
    "ASSIGNED_TO": 0.86,
    "MAINTAINED_BY": 0.86,
    "OPERATED_BY": 0.84,
    "MANAGED_BY": 0.84,
    "ESCALATES_TO": 0.82,

    # ---------------------------------------------------------
    # Governance / policy / process
    # ---------------------------------------------------------
    "GOVERNS": 0.88,
    "ENFORCED_BY": 0.88,
    "DEFINED_IN": 0.82,
    "DOCUMENTED_IN": 0.80,
    "RELATED_POLICY": 0.82,
    "RELATED_SOP": 0.80,
    "RELATED_API": 0.82,
    "RELATED_WORKFLOW": 0.82,

    # ---------------------------------------------------------
    # General documented relationships
    # ---------------------------------------------------------
    "REFERENCES": 0.72,
    "COORDINATES_WITH": 0.70,
    "NOTIFIES": 0.68,
    "RELATED_SYSTEM": 0.72,
    "RELATED_TO": 0.35,
}

    def analyze(
        self,
        graph: nx.MultiDiGraph,
        semantic_scores: dict[UUID, float],
        entity_importance: dict[UUID, float] | None = None,
        max_distance: int = 3,
    ) -> list[ImpactResult]:
        """
        Calculate direct and propagated business impact.

        semantic_scores contains entities with direct semantic evidence
        from retrieval.

        Graph propagation identifies connected entities that may need
        review, but connectivity alone does not make an entity highly
        impacted.
        """

        if not graph.nodes:
            return []

        if not semantic_scores:
            return []

        if max_distance < 0:
            raise ValueError(
                "max_distance must be >= 0"
            )

        importance = entity_importance or {}

        normalized_semantic_scores = {
            entity_id: self._clamp(score)
            for entity_id, score in semantic_scores.items()
            if entity_id in graph
        }

        if not normalized_semantic_scores:
            return []

        results: list[ImpactResult] = []

        undirected_graph = graph.to_undirected()

        for source_entity_id, source_semantic in (
            normalized_semantic_scores.items()
        ):
            source_node = graph.nodes[source_entity_id]
            source_name = source_node["name"]

            # ---------------------------------------------------------
            # 1. DIRECT IMPACT
            # ---------------------------------------------------------

            source_importance = self._clamp(
                importance.get(
                    source_entity_id,
                    0.0,
                )
            )

            direct_score = self._clamp(
                (
                    self.DIRECT_SEMANTIC_WEIGHT
                    * source_semantic
                )
                + (
                    self.DIRECT_IMPORTANCE_WEIGHT
                    * source_importance
                )
            )

            results.append(
                ImpactResult(
                    entity_id=source_entity_id,
                    name=source_node["name"],
                    entity_type=source_node["entity_type"],
                    impact_score=round(
                        direct_score,
                        4,
                    ),
                    impact_level=self._impact_level(
                        direct_score
                    ),
                    impact_origin="DIRECT",
                    impact_category=self._direct_category(
                        source_node["entity_type"]
                    ),
                    semantic_relevance=round(
                        source_semantic,
                        4,
                    ),
                    relationship_strength=1.0,
                    graph_proximity=1.0,
                    entity_importance=round(
                        source_importance,
                        4,
                    ),
                    propagation_distance=0,
                    path=(source_entity_id,),
                    explanation=(
                        f"{source_name} has direct semantic "
                        f"evidence for the requirement. "
                        f"Semantic relevance is "
                        f"{source_semantic:.2f}."
                    ),
                )
            )

            # ---------------------------------------------------------
            # 2. GRAPH PROPAGATION
            # ---------------------------------------------------------

            distances = nx.single_source_shortest_path_length(
                undirected_graph,
                source_entity_id,
                cutoff=max_distance,
            )

            for entity_id, distance in distances.items():

                if entity_id == source_entity_id:
                    continue

                node = graph.nodes[entity_id]

                path = self._shortest_path(
                    undirected_graph,
                    source_entity_id,
                    entity_id,
                )

                if not path:
                    continue

                relationship_strength = (
                    self._calculate_path_relationship_strength(
                        graph,
                        path,
                    )
                )

                graph_proximity = (
                    self._calculate_graph_proximity(
                        distance
                    )
                )

                entity_importance_score = self._clamp(
                    importance.get(
                        entity_id,
                        0.0,
                    )
                )

                # -----------------------------------------------------
                # Propagation must decay with distance AND relationship
                # strength.
                # -----------------------------------------------------

                propagated_semantic = self._clamp(
                    source_semantic
                    * relationship_strength
                    * graph_proximity
                )

                impact_score = self._clamp(
                    (
                        self.PROPAGATED_SEMANTIC_WEIGHT
                        * propagated_semantic
                    )
                    + (
                        self.PROPAGATED_RELATIONSHIP_WEIGHT
                        * relationship_strength
                        * graph_proximity
                    )
                    + (
                        self.PROPAGATED_PROXIMITY_WEIGHT
                        * graph_proximity
                        * entity_importance_score
                    )
                )
                                # -----------------------------------------------------
                # Reject weak propagated impacts.
                #
                # Distance alone must never make an entity appear
                # affected. The propagated result must retain:
                #   1. meaningful semantic relevance
                #   2. a sufficiently strong relationship path
                #   3. a minimum combined impact score
                # -----------------------------------------------------

                thresholds = self.PROPAGATION_THRESHOLDS.get(
                    distance
                )

                if thresholds is None:
                    continue

                if (
                    propagated_semantic
                    < thresholds["semantic"]
                ):
                    continue

                if (
                    relationship_strength
                    < thresholds["relationship"]
                ):
                    continue

                if (
                    impact_score
                    < self.MIN_PROPAGATED_IMPACT_SCORE
                ):
                    continue

                relationship_label = (
                    self._path_relationship_label(
                        graph,
                        path,
                    )
                )

                impact_category = (
                    self._propagated_category(
                        relationship_label
                    )
                )

                explanation = self._build_explanation(
                    source_name=source_name,
                    target_name=node["name"],
                    relationship_type=relationship_label,
                    distance=distance,
                    semantic_relevance=propagated_semantic,
                    relationship_strength=relationship_strength,
                )

                results.append(
                    ImpactResult(
                        entity_id=entity_id,
                        name=node["name"],
                        entity_type=node["entity_type"],
                        impact_score=round(
                            impact_score,
                            4,
                        ),
                        impact_level=self._impact_level(
                            impact_score
                        ),
                        impact_origin="PROPAGATED",
                        impact_category=impact_category,
                        semantic_relevance=round(
                            propagated_semantic,
                            4,
                        ),
                        relationship_strength=round(
                            relationship_strength,
                            4,
                        ),
                        graph_proximity=round(
                            graph_proximity,
                            4,
                        ),
                        entity_importance=round(
                            entity_importance_score,
                            4,
                        ),
                        propagation_distance=distance,
                        path=tuple(path),
                        explanation=explanation,
                    )
                )

        return self._deduplicate_results(results)

    # ------------------------------------------------------------------
    # Relationship calculations
    # ------------------------------------------------------------------

    def _calculate_path_relationship_strength(
        self,
        graph: nx.MultiDiGraph,
        path: list[UUID],
    ) -> float:
        """
        The weakest relationship on a propagation path determines
        the path strength.
        """

        if len(path) < 2:
            return 0.0

        strengths: list[float] = []

        for source, target in zip(
            path,
            path[1:],
        ):
            strength = self._get_edge_strength(
                graph,
                source,
                target,
            )

            if strength > 0.0:
                strengths.append(strength)

        if not strengths:
            return 0.0

        return min(strengths)

    def _get_edge_strength(
        self,
        graph: nx.MultiDiGraph,
        source_entity_id: UUID,
        target_entity_id: UUID,
    ) -> float:
        """
        Return the strongest confidence-adjusted relationship between
        two entities.

        Relationship type provides the base semantic strength.
        Extractor confidence determines how strongly that relationship
        should influence impact propagation.
        """

        strengths: list[float] = []

        for source, target in (
            (
                source_entity_id,
                target_entity_id,
            ),
            (
                target_entity_id,
                source_entity_id,
            ),
        ):
            if not graph.has_edge(
                source,
                target,
            ):
                continue

            edge_data = graph.get_edge_data(
                source,
                target,
            )

            if not edge_data:
                continue

            for data in edge_data.values():
                relationship_type = data.get(
                    "relationship_type"
                )

                if not relationship_type:
                    continue

                base_strength = self._relationship_strength(
                    relationship_type
                )

                if base_strength <= 0.0:
                    continue

                confidence = self._clamp(
                    float(
                        data.get(
                            "confidence",
                            1.0,
                        )
                        or 0.0
                    )
                )

                strengths.append(
                    base_strength * confidence
                )

        if not strengths:
            return 0.0

        return max(strengths)

    def _path_relationship_label(
        self,
        graph: nx.MultiDiGraph,
        path: list[UUID],
    ) -> str:
        """Return a readable relationship path."""

        labels: list[str] = []

        for source, target in zip(
            path,
            path[1:],
        ):
            relationship = (
                self._strongest_relationship_type(
                    graph,
                    source,
                    target,
                )
            )

            if relationship:
                labels.append(relationship)

        if not labels:
            return "CONNECTED"

        return " → ".join(labels)

    def _strongest_relationship_type(
        self,
        graph: nx.MultiDiGraph,
        source_entity_id: UUID,
        target_entity_id: UUID,
    ) -> str | None:
        """Return the strongest relationship between two entities."""

        candidates: list[tuple[float, str]] = []

        for source, target in (
            (
                source_entity_id,
                target_entity_id,
            ),
            (
                target_entity_id,
                source_entity_id,
            ),
        ):
            if not graph.has_edge(
                source,
                target,
            ):
                continue

            edge_data = graph.get_edge_data(
                source,
                target,
            )

            if not edge_data:
                continue

            for data in edge_data.values():
                relationship_type = data.get(
                    "relationship_type"
                )

                if relationship_type:
                    candidates.append(
                        (
                            self._relationship_strength(
                                relationship_type
                            ),
                            relationship_type,
                        )
                    )

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: item[0],
        )[1]

    # ------------------------------------------------------------------
    # Graph helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shortest_path(
        graph: nx.Graph,
        source_entity_id: UUID,
        target_entity_id: UUID,
    ) -> list[UUID]:
        """Return the shortest undirected structural path."""

        try:
            return nx.shortest_path(
                graph,
                source=source_entity_id,
                target=target_entity_id,
            )
        except nx.NetworkXNoPath:
            return []

    @staticmethod
    def _calculate_graph_proximity(
        distance: int,
    ) -> float:
        """
        Convert graph distance into a propagation factor.

        1 hop = 1.0
        2 hops = 0.5
        3 hops = 0.333
        """

        if distance <= 0:
            return 1.0

        return 1.0 / distance

    # ------------------------------------------------------------------
    # Impact classification
    # ------------------------------------------------------------------

    @staticmethod
    def _direct_category(
        entity_type: str,
    ) -> str:
        """
        Classify the action implied by direct semantic evidence.
        """

        normalized_type = entity_type.upper()

        if normalized_type == "TEAM":
            return "STAKEHOLDER"

        if normalized_type in {
            "API",
            "SYSTEM",
            "WORKFLOW",
            "POLICY",
            "DOCUMENTATION",
            "BUSINESS_CONCEPT",
        }:
            return "DIRECT_CHANGE"

        return "REVIEW_REQUIRED"

    @staticmethod
    def _propagated_category(
        relationship_label: str,
    ) -> str:
        """
        Classify propagated impact based on graph relationships.
        """

        relationships = set(
            relationship_label.split(" → ")
        )

        if "OWNED_BY" in relationships:
            return "STAKEHOLDER"

        if "RELATED_TO" in relationships:
            return "INFORMATIONAL"

        return "REVIEW_REQUIRED"

    @staticmethod
    def _impact_level(
        score: float,
    ) -> str:
        """
        Convert impact score into a business impact level.
        """

        if score >= 0.75:
            return "HIGH"

        if score >= 0.50:
            return "MEDIUM"

        if score >= 0.25:
            return "LOW"

        return "MINIMAL"

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    @staticmethod
    def _build_explanation(
        source_name: str,
        target_name: str,
        relationship_type: str,
        distance: int,
        semantic_relevance: float,
        relationship_strength: float,
    ) -> str:

        if distance == 1:
            return (
                f"{target_name} is directly connected to "
                f"{source_name} through {relationship_type}. "
                f"Propagated semantic relevance is "
                f"{semantic_relevance:.2f} and relationship "
                f"strength is {relationship_strength:.2f}."
            )

        return (
            f"{target_name} is {distance} graph hops from "
            f"{source_name} through {relationship_type}. "
            f"Propagated semantic relevance is "
            f"{semantic_relevance:.2f} and relationship "
            f"strength is {relationship_strength:.2f}."
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @classmethod
    def _relationship_strength(
        cls,
        relationship_type: str,
    ) -> float:
        return cls.RELATIONSHIP_STRENGTH.get(
            relationship_type,
            0.0,
        )

    @staticmethod
    def _deduplicate_results(
        results: list[ImpactResult],
    ) -> list[ImpactResult]:
        """Keep the strongest result for each entity."""

        strongest: dict[UUID, ImpactResult] = {}

        for result in results:
            existing = strongest.get(
                result.entity_id
            )

            if (
                existing is None
                or result.impact_score
                > existing.impact_score
            ):
                strongest[result.entity_id] = result

        return sorted(
            strongest.values(),
            key=lambda result: result.impact_score,
            reverse=True,
        )

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            )
        )