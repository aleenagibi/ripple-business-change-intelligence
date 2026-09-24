from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import networkx as nx
import numpy as np
from app.engines.change_understanding_engine import (
    ChangeSpecification,
    ChangeUnderstandingEngine,
)
from app.engines.impact_analysis_engine import (
    ImpactAnalysisEngine,
    ImpactResult,
)
from app.engines.knowledge_graph_engine import KnowledgeGraphEngine
from app.models.entity import BusinessEntity
from app.repositories.entity_repository import EntityRepository
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.retrieval_service import RetrievalService
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ImpactSourceDocument:
    """Source document containing evidence for an impacted entity."""

    document_id: UUID
    filename: str
class ImpactAnalysisService:
    """
    Orchestrates Ripple's complete business change impact pipeline.

    Pipeline:

        Business Requirement
                ↓
        Change Understanding
                ↓
        Hybrid Retrieval
                ↓
        Entity-level Semantic Relevance
                ↓
        Knowledge Graph
                ↓
        Graph Propagation
                ↓
        Impact Scoring
                ↓
        Impact Results
    """

    # Kept as explicit configuration constants so the scoring model
    # remains easy to tune and explain.
    DIRECT_RETRIEVAL_WEIGHT = 0.40
    DIRECT_ENTITY_WEIGHT = 0.60

    ENTITY_DENSE_WEIGHT = 0.75
    ENTITY_LEXICAL_WEIGHT = 0.25

    MIN_ENTITY_SEMANTIC_RELEVANCE = 0.20
    ENTITY_IMPACT_THRESHOLD = 0.50

    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, db: Session) -> None:
        self.db = db

        self.retrieval_service = RetrievalService(db)
        self.knowledge_graph_service = KnowledgeGraphService(db)
        self.entity_repository = EntityRepository(db)

        self.graph_engine = KnowledgeGraphEngine()
        self.impact_engine = ImpactAnalysisEngine()

        self.change_engine = ChangeUnderstandingEngine()

        self.embedding_model = self._load_embedding_model(
            self.EMBEDDING_MODEL_NAME
        )

    @staticmethod
    @lru_cache(maxsize=2)
    def _load_embedding_model(
        model_name: str,
    ) -> SentenceTransformer:
        """
        Load and cache the sentence-transformer model.

        The model is cached at process level to avoid repeatedly
        loading the same embedding model for every request.
        """

        return SentenceTransformer(model_name)

    def analyze(
        self,
        organization_id: UUID,
        query: str,
        top_k: int = 10,
        max_distance: int = 3,
    ) -> list[ImpactResult]:
        """
        Analyze the business impact of a requirement change.

        The requirement is first interpreted to identify structured
        change information such as:

            - subject
            - old value
            - new value
            - change type
            - direction
            - magnitude
            - business concepts

        Hybrid retrieval identifies relevant document chunks.

        Entity-level semantic analysis combines:

            - hybrid retrieval evidence
            - dense semantic similarity
            - lexical similarity
            - exact entity-name evidence

        The knowledge graph then propagates impact through documented
        business relationships.
        """

        if not query.strip():
            return []

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if max_distance < 0:
            raise ValueError(
                "max_distance must be >= 0"
            )

        # -------------------------------------------------------------
        # 1. UNDERSTAND THE CHANGE
        # -------------------------------------------------------------

        change_specification = self.change_engine.analyze(
            query
        )

        retrieval_query = (
            change_specification.retrieval_query
        )

        # -------------------------------------------------------------
        # 2. HYBRID RETRIEVAL
        # -------------------------------------------------------------

        # Impact analysis needs a broader evidence pool than the final
        # number of returned impact results. Important policies,
        # workflows, APIs, SOPs and team documents can occur below the
        # first few fused retrieval results.
        retrieval_top_k = max(
            top_k * 2,
            20,
        )

        hybrid_results = (
            self.retrieval_service.search_hybrid(
                organization_id=organization_id,
                query=retrieval_query,
                top_k=retrieval_top_k,
            )
        )

        if not hybrid_results:
            return []

        # -------------------------------------------------------------
        # 3. BUILD ORGANIZATION KNOWLEDGE GRAPH
        # -------------------------------------------------------------

        graph = (
            self.knowledge_graph_service.build_for_organization(
                organization_id
            )
        )

        if not graph.nodes:
            return []

        # -------------------------------------------------------------
        # 4. ENTITY-LEVEL SEMANTIC RELEVANCE
        # -------------------------------------------------------------

        semantic_scores = (
            self._build_entity_semantic_scores(
                query=retrieval_query,
                hybrid_results=hybrid_results,
                graph=graph,
            )
        )

        print("[IMPACT DEBUG] TOP DIRECT SEEDS")
        for entity_id, score in sorted(
            semantic_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:30]:
            entity = graph.nodes.get(entity_id, {})
            print(
                f"  {score:.4f} | "
                f"{entity.get('entity_type')} | "
                f"{entity.get('name')}"
            )

        print(
            f"[IMPACT DEBUG] "
            f"hybrid_results={len(hybrid_results)} "
            f"direct_seed_entities={len(semantic_scores)} "
            f"graph_nodes={graph.number_of_nodes()} "
            f"graph_edges={graph.number_of_edges()}"
        )

        if not semantic_scores:
            return []

        # -------------------------------------------------------------
        # 5. ENTITY STRUCTURAL IMPORTANCE
        # -------------------------------------------------------------

        entity_importance = (
            self._calculate_entity_importance(
                graph
            )
        )

        # -------------------------------------------------------------
        # 6. IMPACT ANALYSIS + GRAPH PROPAGATION
        # -------------------------------------------------------------

        results = self.impact_engine.analyze(
            graph=graph,
            semantic_scores=semantic_scores,
            entity_importance=entity_importance,
            max_distance=max_distance,
        )

        # -------------------------------------------------------------
        # 7. ENRICH RESULTS WITH CHANGE CONTEXT
        # -------------------------------------------------------------

        return self._enrich_results_with_change(
            results=results,
            change_specification=change_specification,
        )

    def _build_entity_semantic_scores(
        self,
        *,
        query: str,
        hybrid_results,
        graph: nx.Graph,
    ) -> dict[UUID, float]:
        """
        Build semantic relevance scores for canonical entities using
        absolute retrieval evidence followed by entity-level semantic
        refinement.

        Important design rule:
            Retrieval establishes whether a query is relevant to the
            organization's knowledge base.

            Entity similarity only refines that retrieved evidence.

            Entity similarity must never manufacture relevance for an
            unrelated query.

        TF-IDF and dense scores are treated as absolute relevance signals.
        RRF is used only for ranking and is deliberately not normalized
        against the top result because RRF is a rank-fusion score rather
        than a semantic similarity score.
        """

        if not query.strip() or not hybrid_results:
            return {}

        # -------------------------------------------------------------
        # 1. RETRIEVED CHUNK EVIDENCE
        # -------------------------------------------------------------

        chunk_ids = {
            result.chunk_id
            for result in hybrid_results
            if result.chunk_id is not None
        }

        if not chunk_ids:
            return {}

        entities_by_chunk: dict[UUID, list] = {}

        for chunk_id in chunk_ids:
            entities = self.entity_repository.list_for_chunk(
                chunk_id
            )

            if entities:
                entities_by_chunk[chunk_id] = entities

        if not entities_by_chunk:
            return {}

        # -------------------------------------------------------------
        # 2. ABSOLUTE RETRIEVAL RELEVANCE GATE
        # -------------------------------------------------------------
        #
        # RRF is intentionally NOT used as the relevance threshold.
        #
        # RRF answers:
        #     "How highly did this chunk rank?"
        #
        # It does NOT answer:
        #     "Is this query actually relevant to this chunk?"
        #
        # The raw TF-IDF and dense scores provide the latter signal.
        #
        # Thresholds are deliberately conservative:
        #
        #   dense >= 0.20
        #       OR
        #   TF-IDF >= 0.08
        #
        # A chunk must pass at least one absolute relevance test before
        # its entities can participate in impact analysis.
        # -------------------------------------------------------------

        MIN_DENSE_CHUNK_RELEVANCE = 0.20
        MIN_TFIDF_CHUNK_RELEVANCE = 0.08

        relevant_chunks: list[tuple[object, float]] = []

        for result in hybrid_results:
            dense_score = (
                float(result.dense_score)
                if result.dense_score is not None
                else 0.0
            )

            tfidf_score = (
                float(result.tfidf_score)
                if result.tfidf_score is not None
                else 0.0
            )

            # Dense cosine similarity can be negative.
            dense_relevance = max(
                0.0,
                min(1.0, dense_score),
            )

            # TF-IDF cosine similarity is also bounded to [0, 1],
            # but protect against unexpected numerical values.
            tfidf_relevance = max(
                0.0,
                min(1.0, tfidf_score),
            )

            passes_dense_gate = (
                dense_relevance
                >= MIN_DENSE_CHUNK_RELEVANCE
            )

            passes_tfidf_gate = (
                tfidf_relevance
                >= MIN_TFIDF_CHUNK_RELEVANCE
            )

            if not (
                passes_dense_gate
                or passes_tfidf_gate
            ):
                continue

            # TF-IDF and dense retrieval are different signals.
            # We use the stronger absolute signal as the chunk's
            # relevance evidence rather than treating their raw scales
            # as identical.
            chunk_relevance = max(
                dense_relevance,
                tfidf_relevance,
            )

            relevant_chunks.append(
                (
                    result,
                    chunk_relevance,
                )
            )

        # -------------------------------------------------------------
        # 3. QUERY-LEVEL RELEVANCE GATE
        # -------------------------------------------------------------
        #
        # If no retrieved chunk is sufficiently relevant, the query has
        # no reliable evidence in the organization's corpus.
        #
        # Return no entity scores instead of allowing the graph to
        # generate false-positive impact.
        # -------------------------------------------------------------

        if not relevant_chunks:
            return {}

        # -------------------------------------------------------------
        # 4. MAP RETRIEVED EVIDENCE TO CANONICAL ENTITIES
        # -------------------------------------------------------------

        canonical_entities: dict[UUID, object] = {}
        entity_evidence: dict[UUID, float] = {}
        entity_occurrences: dict[UUID, int] = {}

        for rank, (
            result,
            chunk_relevance,
        ) in enumerate(
            relevant_chunks,
            start=1,
        ):
            chunk_id = result.chunk_id

            # Rank is only a secondary confidence factor.
            # It cannot make an irrelevant chunk relevant because the
            # absolute relevance gate above has already been applied.
            rank_factor = 1.0 / np.sqrt(rank)

            chunk_evidence = (
                0.80 * chunk_relevance
                + 0.20 * rank_factor
            )

            for entity in entities_by_chunk.get(
                chunk_id,
                [],
            ):
                canonical_entity_id = (
                    entity.canonical_entity_id
                )

                # Mention-level entities that have not yet been
                # reconciled to a canonical entity cannot safely
                # participate in graph propagation.
                if canonical_entity_id is None:
                    continue

                if canonical_entity_id not in graph:
                    continue

                if canonical_entity_id not in canonical_entities:
                    canonical_entities[
                        canonical_entity_id
                    ] = entity

                previous = entity_evidence.get(
                    canonical_entity_id,
                    0.0,
                )

                if previous == 0.0:
                    updated_evidence = chunk_evidence
                else:
                    # Repeated evidence strengthens confidence with
                    # diminishing returns.
                    updated_evidence = min(
                        1.0,
                        previous
                        + (
                            0.50
                            * chunk_evidence
                        ),
                    )

                entity_evidence[
                    canonical_entity_id
                ] = updated_evidence

                entity_occurrences[
                    canonical_entity_id
                ] = (
                    entity_occurrences.get(
                        canonical_entity_id,
                        0,
                    )
                    + 1
                )

        if not canonical_entities:
            return {}

        # -------------------------------------------------------------
        # 5. BUILD ENTITY CONTEXTS
        # -------------------------------------------------------------

        entity_ids = list(
            canonical_entities.keys()
        )

        entity_contexts: list[str] = []

        for entity_id in entity_ids:
            entity = canonical_entities[
                entity_id
            ]

            parts = [
                entity.name,
            ]

            if entity.description:
                parts.append(
                    entity.description
                )

            entity_contexts.append(
                " ".join(parts)
            )

        # -------------------------------------------------------------
        # 6. DENSE ENTITY SEMANTIC SIMILARITY
        # -------------------------------------------------------------

        embeddings = (
            self.embedding_model.encode(
                [
                    query,
                    *entity_contexts,
                ],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        ).astype(np.float32)

        query_embedding = embeddings[0]

        entity_embeddings = embeddings[1:]

        dense_similarities = np.dot(
            entity_embeddings,
            query_embedding,
        )

        dense_similarities = np.clip(
            dense_similarities,
            0.0,
            1.0,
        )

        # -------------------------------------------------------------
        # 7. LEXICAL ENTITY SIMILARITY
        # -------------------------------------------------------------

        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )

        matrix = vectorizer.fit_transform(
            [
                query,
                *entity_contexts,
            ]
        )

        lexical_similarities = cosine_similarity(
            matrix[0],
            matrix[1:],
        )[0]

        lexical_similarities = np.clip(
            lexical_similarities,
            0.0,
            1.0,
        )

        # -------------------------------------------------------------
        # 8. ENTITY-LEVEL SCORE
        # -------------------------------------------------------------

        query_lower = query.lower()

        semantic_scores: dict[
            UUID,
            float,
        ] = {}

        for index, entity_id in enumerate(
            entity_ids
        ):
            entity = canonical_entities[
                entity_id
            ]

            dense_similarity = float(
                dense_similarities[index]
            )

            lexical_similarity = float(
                lexical_similarities[index]
            )

            entity_similarity = (
                self.ENTITY_DENSE_WEIGHT
                * dense_similarity
                + self.ENTITY_LEXICAL_WEIGHT
                * lexical_similarity
            )

            entity_similarity = float(
                np.clip(
                    entity_similarity,
                    0.0,
                    1.0,
                )
            )

            entity_name = (
                entity.name.strip().lower()
                if entity.name
                else ""
            )

            exact_match = (
                1.0
                if entity_name
                and entity_name in query_lower
                else 0.0
            )

            occurrence_bonus = min(
                0.10,
                0.03
                * max(
                    0,
                    entity_occurrences.get(
                        entity_id,
                        1,
                    )
                    - 1,
                ),
            )

            retrieval_evidence = entity_evidence.get(
                entity_id,
                0.0,
            )

            # ---------------------------------------------------------
            # IMPORTANT:
            #
            # Entity similarity is multiplied by retrieval evidence.
            #
            # Therefore:
            #
            #     retrieval evidence = 0
            #         -> entity score = 0
            #
            # A semantically similar entity cannot become an impact
            # candidate unless the query first retrieved relevant
            # document evidence.
            # ---------------------------------------------------------

            combined_score = (
                self.DIRECT_RETRIEVAL_WEIGHT
                * retrieval_evidence
                + self.DIRECT_ENTITY_WEIGHT
                * entity_similarity
            )

            # Exact identifier/name matches are useful evidence, but
            # they are deliberately bounded so that they cannot bypass
            # the retrieval gate.
            if exact_match > 0.0:
                combined_score += (
                    0.05
                    * retrieval_evidence
                )

            combined_score += (
                occurrence_bonus
                * retrieval_evidence
            )

            combined_score = float(
                np.clip(
                    combined_score,
                    0.0,
                    1.0,
                )
            )
            if combined_score >= 0.70:
                print(
                    "[IMPACT DEBUG] "
                    f"{entity.name} | "
                    f"retrieval={retrieval_evidence:.4f} | "
                    f"entity_similarity={entity_similarity:.4f} | "
                    f"combined={combined_score:.4f}"
    )
            # Final entity-level minimum.
            #
            # This removes very weak candidates that survived the
            # chunk-level gate while preserving genuinely supported
            # entities.
            if retrieval_evidence < 0.15:
                continue

            if entity_similarity < self.MIN_ENTITY_SEMANTIC_RELEVANCE:
                continue

            if combined_score < self.ENTITY_IMPACT_THRESHOLD:
                continue

            semantic_scores[
                entity_id
            ] = combined_score

        return semantic_scores
    @staticmethod
    def _coerce_uuid(
        value,
    ) -> UUID | None:
        """
        Normalize UUID-like values returned by repositories and
        retrieval engines.

        SQLAlchemy repository layers may return UUID objects while
        serialized result objects may contain strings.
        """

        if isinstance(value, UUID):
            return value

        if value is None:
            return None

        try:
            return UUID(str(value))
        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return None

    @staticmethod
    def _calculate_entity_importance(
        graph: nx.MultiDiGraph,
    ) -> dict[UUID, float]:
        """
        Estimate entity importance from graph connectivity.

        Degree centrality provides a deterministic and explainable
        structural importance measure.
        """

        if not graph.nodes:
            return {}

        centrality = nx.degree_centrality(
            graph.to_undirected()
        )

        return {
            entity_id: min(
                max(
                    float(score),
                    0.0,
                ),
                1.0,
            )
            for entity_id, score in centrality.items()
        }

    @staticmethod
    def _enrich_results_with_change(
        results: list[ImpactResult],
        change_specification: ChangeSpecification,
    ) -> list[ImpactResult]:
        """
        Add interpreted change context to impact explanations.

        The underlying impact score remains unchanged.

        This method deliberately does not alter the scoring model;
        it makes the final result explain the relationship between
        the detected requirement change and the affected entity.
        """

        if not results:
            return results

        if not change_specification.is_structured_change:
            return results

        change_description = (
            ImpactAnalysisService._format_change_description(
                change_specification
            )
        )

        enriched: list[ImpactResult] = []

        for result in results:
            explanation = (
                f"{change_description} "
                f"{result.explanation}"
            )

            enriched.append(
                ImpactResult(
                    entity_id=result.entity_id,
                    name=result.name,
                    entity_type=result.entity_type,
                    impact_score=result.impact_score,
                    impact_level=result.impact_level,
                    impact_origin=result.impact_origin,
                    impact_category=result.impact_category,
                    semantic_relevance=result.semantic_relevance,
                    relationship_strength=result.relationship_strength,
                    graph_proximity=result.graph_proximity,
                    entity_importance=result.entity_importance,
                    propagation_distance=result.propagation_distance,
                    path=result.path,
                    explanation=explanation,
                )
            )

        return enriched

    @staticmethod
    def _format_change_description(
        change_specification: ChangeSpecification,
    ) -> str:
        """
        Convert a structured change specification into concise
        human-readable context.
        """

        subject = (
            change_specification.subject.strip()
            if change_specification.subject
            else "the requirement"
        )

        old_value = (
            change_specification.old_value.raw
            if change_specification.old_value
            else None
        )

        new_value = (
            change_specification.new_value.raw
            if change_specification.new_value
            else None
        )

        if old_value and new_value:
            return (
                f"The requirement changes {subject} "
                f"from {old_value} to {new_value}. "
            )

        if change_specification.change_type == "REPLACEMENT":
            return (
                f"The requirement replaces {subject}. "
            )

        return (
            f"The requirement changes {subject}. "
        )
