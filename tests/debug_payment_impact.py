from uuid import UUID

from app.db.database import SessionLocal
from app.services.impact_analysis_service import ImpactAnalysisService


ORGANIZATION_ID = UUID(
    "b5154ce1-c734-489e-a769-880535ceebcd"
)

QUERY = (
    "The primary payment gateway vendor will now charge "
    "an additional 2% processing fee on all international transactions."
)


def main() -> None:
    db = SessionLocal()

    try:
        service = ImpactAnalysisService(db)

        print("=" * 70)
        print("RIPPLE IMPACT ANALYSIS DEBUG")
        print("=" * 70)
        print(f"QUERY: {QUERY}")
        print()

        # --------------------------------------------------
        # 1. HYBRID RETRIEVAL
        # --------------------------------------------------

        hybrid_results = (
            service.retrieval_service.search_hybrid(
                organization_id=ORGANIZATION_ID,
                query=QUERY,
                top_k=10,
            )
        )

        print("1. HYBRID RETRIEVAL")
        print("-" * 70)
        print(f"RESULTS: {len(hybrid_results)}")

        for result in hybrid_results:
            print(
                f"{result.chunk_id}"
                f" | hybrid={result.score:.6f}"
                f" | tfidf_rank={result.tfidf_rank}"
                f" | dense_rank={result.dense_rank}"
                f" | tfidf={result.tfidf_score:.6f}"
                f" | dense={result.dense_score:.6f}"
            )

        print()

        if not hybrid_results:
            print("❌ HYBRID RETRIEVAL IS EMPTY.")
            print("The problem is before entity mapping.")
            return

        # --------------------------------------------------
        # 2. KNOWLEDGE GRAPH
        # --------------------------------------------------

        graph = (
            service.knowledge_graph_service
            .build_for_organization(
                ORGANIZATION_ID
            )
        )

        print("2. KNOWLEDGE GRAPH")
        print("-" * 70)
        print(f"NODES: {graph.number_of_nodes()}")
        print(f"EDGES: {graph.number_of_edges()}")
        print()

        # --------------------------------------------------
        # 3. FULL IMPACT ANALYSIS
        # --------------------------------------------------

        results = service.analyze(
            organization_id=ORGANIZATION_ID,
            query=QUERY,
            top_k=10,
            max_distance=3,
        )

        print("3. IMPACT ANALYSIS")
        print("-" * 70)
        print(f"RESULTS: {len(results)}")
        print()

        for result in results:
            print(
                f"{result.name}"
                f" | type={result.entity_type}"
                f" | impact={result.impact_score:.4f}"
                f" | level={result.impact_level}"
                f" | semantic={result.semantic_relevance:.4f}"
                f" | relationship={result.relationship_strength:.4f}"
                f" | proximity={result.graph_proximity:.4f}"
                f" | importance={result.entity_importance:.4f}"
                f" | distance={result.propagation_distance}"
            )

            print(f"  explanation: {result.explanation}")
            print()

        if not results:
            print("❌ IMPACT ANALYSIS IS EMPTY.")
            print(
                "Hybrid retrieval has results, "
                "but entity mapping/scoring is filtering them."
            )
        else:
            print("✅ IMPACT ANALYSIS RETURNED RESULTS.")

        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()