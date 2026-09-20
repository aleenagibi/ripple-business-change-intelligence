import uuid

from app.db.database import SessionLocal
from app.engines.relationship_extraction_engine import (
    RelationshipExtractionEngine,
)
from app.models.entity import BusinessEntity

TEXT = """
The Payment API uses the Payment Gateway.
The Payment Gateway supports the Checkout Workflow.
"""


def make_entity(name: str) -> BusinessEntity:
    return BusinessEntity(
        id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        name=name,
        normalized_name=name.lower(),
        entity_type="BUSINESS_CONCEPT",
    )


entities = [
    make_entity("Payment API"),
    make_entity("Payment Gateway"),
    make_entity("Checkout Workflow"),
]

engine = RelationshipExtractionEngine()

relationships = engine.extract(
    entities=entities,
    text=TEXT,
)

print("=" * 60)
print("RELATIONSHIP ENGINE TEST")
print("=" * 60)

print(f"ENTITIES: {len(entities)}")
print(f"RELATIONSHIPS: {len(relationships)}")
print()

for relationship in relationships:
    print(
        relationship.relationship_type,
        "|",
        relationship.confidence,
        "|",
        relationship.evidence,
    )

print("=" * 60)