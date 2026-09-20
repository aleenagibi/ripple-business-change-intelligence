import uuid

from app.engines.knowledge_graph_engine import KnowledgeGraphEngine
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship


def make_entity(name: str) -> BusinessEntity:
    return BusinessEntity(
        id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        name=name,
        normalized_name=name.lower(),
        entity_type="BUSINESS_CONCEPT",
    )


payment_api = make_entity("Payment API")
payment_gateway = make_entity("Payment Gateway")
checkout_workflow = make_entity("Checkout Workflow")


uses_relationship = EntityRelationship(
    id=uuid.uuid4(),
    source_entity_id=payment_api.id,
    target_entity_id=payment_gateway.id,
    relationship_type="USES",
    confidence=0.90,
    evidence_chunk_id=uuid.uuid4(),
    evidence="The Payment API uses the Payment Gateway.",
)

supports_relationship = EntityRelationship(
    id=uuid.uuid4(),
    source_entity_id=payment_gateway.id,
    target_entity_id=checkout_workflow.id,
    relationship_type="SUPPORTS",
    confidence=0.90,
    evidence_chunk_id=uuid.uuid4(),
    evidence="The Payment Gateway supports the Checkout Workflow.",
)


engine = KnowledgeGraphEngine()

graph = engine.build(
    entities=[
        payment_api,
        payment_gateway,
        checkout_workflow,
    ],
    relationships=[
        uses_relationship,
        supports_relationship,
    ],
)


print("=" * 60)
print("KNOWLEDGE GRAPH ENGINE TEST")
print("=" * 60)

print(f"NODES: {engine.node_count()}")
print(f"EDGES: {engine.edge_count()}")
print()


print("DIRECT NEIGHBORS OF PAYMENT API:")

neighbors = engine.get_direct_neighbors(
    payment_api.id
)

for node in neighbors:
    print(
        f"  {node.name} | {node.entity_type}"
    )

print()


print("RELATIONSHIP:")

relationships = engine.get_relationships(
    payment_api.id,
    payment_gateway.id,
)

for relationship in relationships:
    print(
        f"  {relationship.relationship_type} | "
        f"{relationship.confidence} | "
        f"{relationship.evidence}"
    )

print()


print("SHORTEST PATH:")

path = engine.shortest_path(
    payment_api.id,
    checkout_workflow.id,
)

for node_id in path:
    node = engine.get_entity(node_id)

    if node:
        print(f"  → {node.name}")

print()


print("ENTITIES WITHIN DISTANCE 2:")

nearby = engine.get_entities_within_distance(
    payment_api.id,
    max_distance=2,
)

for node in nearby:
    print(
        f"  {node.name} | {node.entity_type}"
    )

print("=" * 60)