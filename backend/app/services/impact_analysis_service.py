from __future__ import annotations

from functools import lru_cache
from uuid import UUID

import networkx as nx
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
    ENTITY_SIMILARITY_WEIGHT = 0.70
    CHUNK_RELEVANCE_WEIGHT = 0.30

    ENTITY_DENSE_WEIGHT = 0.75
    ENTITY_LEXICAL_WEIGHT = 0.25

    ENTITY_IMPACT_THRESHOLD = 0.35

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
        query: str,
        hybrid_results,
        graph: nx.MultiDiGraph,
    ) -> dict[UUID, float]:
        """
        Build evidence-backed direct semantic scores for canonical
        entities found in retrieved document chunks.

        Evidence is intentionally layered:

            1. Hybrid retrieval evidence
            2. Entity-level dense semantic similarity
            3. Entity-level lexical similarity
            4. Exact entity-name match

        Retrieval evidence is the primary signal.

        This prevents a generic phrase such as "4 business hours"
        from outranking source artifacts such as policies, APIs,
        workflows and teams merely because the artifact name is less
        similar to the full requirement sentence.

        The method uses only fields exposed by the current HybridResult:

            - score
            - chunk_id
            - retrieval rank

        The hybrid RRF score is NOT treated as a cosine similarity.
        It is used only as relative retrieval evidence.
        """

        if not query.strip() or not hybrid_results:
            return {}

        # -------------------------------------------------------------
        # 1. LOAD ENTITIES BELONGING TO RETRIEVED CHUNKS
        # -------------------------------------------------------------

        chunk_ids: set[UUID] = set()

        for result in hybrid_results:
            chunk_id = self._coerce_uuid(
                result.chunk_id
            )

            if chunk_id is not None:
                chunk_ids.add(chunk_id)

        if not chunk_ids:
            return {}

        entities_by_chunk: dict[
            UUID,
            list[BusinessEntity],
        ] = {}

        for chunk_id in chunk_ids:
            entities_by_chunk[chunk_id] = (
                self.entity_repository.list_for_chunk(
                    chunk_id
                )
            )

        # -------------------------------------------------------------
        # 2. COLLECT CANONICAL ENTITY RETRIEVAL EVIDENCE
        # -------------------------------------------------------------

        canonical_entities: dict[
            UUID,
            BusinessEntity,
        ] = {}

        entity_evidence: dict[
            UUID,
            float,
        ] = {}

        entity_occurrences: dict[
            UUID,
            int,
        ] = {}

        top_rrf_score = max(
            float(
                getattr(
                    hybrid_results[0],
                    "score",
                    0.0,
                )
                or 0.0
            ),
            1e-8,
        )

        for rank, result in enumerate(
            hybrid_results,
            start=1,
        ):
            chunk_id = self._coerce_uuid(
                result.chunk_id
            )

            if chunk_id is None:
                continue

            rrf_score = max(
                float(
                    getattr(
                        result,
                        "score",
                        0.0,
                    )
                    or 0.0
                ),
                0.0,
            )

            # ---------------------------------------------------------
            # RRF IS A FUSION SCORE, NOT A COSINE SIMILARITY
            # ---------------------------------------------------------
            #
            # Normalize relative to the strongest retrieved result.
            # This gives us a stable retrieval-evidence signal without
            # pretending that RRF has the same meaning as dense cosine
            # similarity.
            #
            normalized_rrf = min(
                rrf_score / top_rrf_score,
                1.0,
            )

            # Rank decay gives higher-ranked chunks stronger evidence.
            rank_factor = 1.0 / np.sqrt(rank)

            chunk_evidence = (
                0.70 * normalized_rrf
                + 0.30 * rank_factor
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
                    # Repeated evidence from additional retrieved
                    # chunks strengthens confidence with diminishing
                    # returns.
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
        # 3. BUILD ENTITY CONTEXTS
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
        # 4. DENSE SEMANTIC SIMILARITY
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
        # 5. LEXICAL SIMILARITY
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
        # 6. EXACT ENTITY / IDENTIFIER EVIDENCE
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

            entity_similarity = min(
                max(
                    entity_similarity,
                    0.0,
                ),
                1.0,
            )

            retrieval_evidence = min(
                max(
                    entity_evidence.get(
                        entity_id,
                        0.0,
                    ),
                    0.0,
                ),
                1.0,
            )

            entity_name = (
                entity.name.strip().lower()
            )

            # Exact identifiers such as RATE-409, RDP-002 and
            # API-RE-007 receive an explicit lexical anchor when the
            # requirement directly names them.
            exact_match = (
                1.0
                if entity_name
                and entity_name in query_lower
                else 0.0
            )

            # Repeated mentions across multiple retrieved chunks
            # provide additional corpus evidence.
            occurrence_bonus = min(
                0.10,
                0.03
                * max(
                    entity_occurrences.get(
                        entity_id,
                        1,
                    )
                    - 1,
                    0,
                ),
            )

            # ---------------------------------------------------------
            # FINAL DIRECT EVIDENCE SCORE
            # ---------------------------------------------------------
            #
            # Retrieval evidence is intentionally the strongest signal.
            #
            # This is critical for Ripple:
            #
            #     requirement
            #          ↓
            #     relevant document
            #          ↓
            #     entity mentioned in document
            #          ↓
            #     canonical entity
            #
            # should be stronger evidence than simply having an entity
            # name that happens to resemble the requirement text.
            #
            combined_score = (
                0.55 * retrieval_evidence
                + 0.30 * entity_similarity
                + 0.10 * exact_match
                + occurrence_bonus
            )

            combined_score = min(
                max(
                    combined_score,
                    0.0,
                ),
                1.0,
            )

            # An entity must have meaningful evidence from the
            # retrieved organization corpus. Semantic similarity alone
            # cannot introduce a new direct impact seed.
            if retrieval_evidence < 0.15:
                continue

            if combined_score < 0.25:
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