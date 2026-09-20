from uuid import UUID

from app.db.database import SessionLocal
from app.services.impact_analysis_service import ImpactAnalysisService


ORGANIZATION_ID = UUID(
    "b5154ce1-c734-489e-a769-880535ceebcd"
)

QUERY = "Payment processing changes"


def main() -> None:
    print("=" * 60)
    print("IMPACT ANALYSIS SERVICE DEBUG TEST")
    print("=" * 60)

    db = SessionLocal()

    try:
        service = ImpactAnalysisService(db)

        print(f"ORGANIZATION: {ORGANIZATION_ID}")
        print(f"QUERY: {QUERY}")
        print()

        # --------------------------------------------------
        # 1. TEST HYBRID RETRIEVAL
        # --------------------------------------------------

        hybrid_results = service.retrieval_service.search_hybrid(
            organization_id=ORGANIZATION_ID,
            query=QUERY,
            top_k=10,
        )

        print("HYBRID RETRIEVAL")
        print("-" * 60)
        print(f"RESULTS: {len(hybrid_results)}")

        for result in hybrid_results:
            print(
                f"  chunk={result.chunk_id}"
                f" | score={result.score:.6f}"
                f" | tfidf_rank={result.tfidf_rank}"
                f" | dense_rank={result.dense_rank}"
            )

        print()

        if not hybrid_results:
            print("NO HYBRID RESULTS.")
            print("The problem is before entity mapping.")
            return

        # --------------------------------------------------
        # 2. BUILD KNOWLEDGE GRAPH
        # --------------------------------------------------

        graph = (
            service.knowledge_graph_service
            .build_for_organization(
                ORGANIZATION_ID
            )
        )

        print("KNOWLEDGE GRAPH")
        print("-" * 60)
        print(f"NODES: {graph.number_of_nodes()}")
        print(f"EDGES: {graph.number_of_edges()}")
        print()

        # --------------------------------------------------
        # 3. BUILD ENTITY SEMANTIC SCORES
        # --------------------------------------------------

        semantic_scores = (
            service._build_entity_semantic_scores(
                 query=QUERY,
                hybrid_results=hybrid_results,
                graph=graph,
            )
        )

        print("ENTITY SEMANTIC SCORES")
        print("-" * 60)
        print(f"ENTITIES: {len(semantic_scores)}")

        for entity_id, score in semantic_scores.items():
            node = graph.nodes[entity_id]

            print(
                f"  {node['name']}"
                f" | {node['entity_type']}"
                f" | relevance={score:.4f}"
            )

        print()

        if not semantic_scores:
            print("NO ENTITY SEMANTIC SCORES.")
            print("The problem is chunk → entity mapping.")
            return

        # --------------------------------------------------
        # 4. RUN COMPLETE SERVICE
        # --------------------------------------------------

        results = service.analyze(
            organization_id=ORGANIZATION_ID,
            query=QUERY,
            top_k=10,
            max_distance=3,
        )

        print("FINAL IMPACT ANALYSIS")
        print("-" * 60)
        print(f"IMPACTED ENTITIES: {len(results)}")
        print()

        for result in results:
            print(
                f"{result.name}"
                f" | {result.entity_type}"
                f" | score={result.impact_score:.4f}"
                f" | level={result.impact_level}"
                f" | distance={result.propagation_distance}"
            )

            print(
                f"  relationship: "
                f"{result.relationship_strength:.4f}"
            )

            print(
                f"  semantic relevance: "
                f"{result.semantic_relevance:.4f}"
            )

            print(
                f"  explanation: "
                f"{result.explanation}"
            )

            print(
                "  path: "
                + " -> ".join(
                    map(str, result.path)
                )
            )

            print()

        print("=" * 60)
        print("DEBUG TEST COMPLETED")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()