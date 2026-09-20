from uuid import uuid4

import networkx as nx
from app.engines.impact_analysis_engine import ImpactAnalysisEngine
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship


def create_entity(
    name: str,
    entity_type: str,
) -> BusinessEntity:
    return BusinessEntity(
        id=uuid4(),
        chunk_id=uuid4(),
        name=name,
        normalized_name=name.lower(),
        entity_type=entity_type,
        description=None,
    )


def create_relationship(
    source_id,
    target_id,
    relationship_type: str,
) -> EntityRelationship:
    return EntityRelationship(
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=relationship_type,
        confidence=0.90,
        evidence_chunk_id=uuid4(),
        evidence=f"Relationship between entities: {relationship_type}",
        )


def main() -> None:
    print("=" * 60)
    print("IMPACT ANALYSIS ENGINE TEST")
    print("=" * 60)

    payment = create_entity(
        "Payment",
        "BUSINESS_CONCEPT",
    )

    payment_api = create_entity(
        "Payment API",
        "API",
    )

    payment_gateway = create_entity(
        "Payment Gateway",
        "SYSTEM",
    )

    checkout_workflow = create_entity(
        "Checkout Workflow",
        "WORKFLOW",
    )

    entities = [
        payment,
        payment_api,
        payment_gateway,
        checkout_workflow,
    ]

    relationships = [
        create_relationship(
            payment.id,
            payment_api.id,
            "USES",
        ),
        create_relationship(
            payment_api.id,
            payment_gateway.id,
            "USES",
        ),
        create_relationship(
            payment_gateway.id,
            checkout_workflow.id,
            "SUPPORTS",
        ),
    ]

    graph = nx.MultiDiGraph()

    for entity in entities:
        graph.add_node(
            entity.id,
            name=entity.name,
            normalized_name=entity.normalized_name,
            entity_type=entity.entity_type,
            description=entity.description,
        )

    for relationship in relationships:
        graph.add_edge(
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship_type=relationship.relationship_type,
            confidence=relationship.confidence,
            evidence=relationship.evidence,
        )

    engine = ImpactAnalysisEngine()

    semantic_scores = {
        payment.id: 0.95,
    }

    entity_importance = {
        payment.id: 0.90,
        payment_api.id: 0.85,
        payment_gateway.id: 0.80,
        checkout_workflow.id: 0.75,
    }

    results = engine.analyze(
        graph=graph,
        semantic_scores=semantic_scores,
        entity_importance=entity_importance,
        max_distance=3,
    )

    print()
    print("SEMANTICALLY MATCHED ENTITY:")
    print("Payment | relevance: 0.95")

    print()
    print("IMPACTED ENTITIES:")
    print("-" * 60)

    for result in results:
        print(
            f"{result.name} | "
            f"{result.entity_type} | "
            f"score: {result.impact_score:.4f} | "
            f"level: {result.impact_level} | "
            f"distance: {result.propagation_distance}"
        )

        print(
            f"  relationship: "
            f"{result.relationship_strength:.2f}"
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
                str(node_id)
                for node_id in result.path
            )
        )

        print()

    print("=" * 60)


if __name__ == "__main__":
    main()