from app.db.database import SessionLocal
from app.services.relationship_service import RelationshipService

ORGANIZATION_ID = "b5154ce1-c734-489e-a769-880535ceebcd"


db = SessionLocal()

try:
    service = RelationshipService(db)

    print("=" * 60)
    print("RELATIONSHIP PROCESSING TEST")
    print("=" * 60)

    relationships = service.process_organization(
        ORGANIZATION_ID
    )

    print(
        f"EXTRACTED & PERSISTED: {len(relationships)}"
    )
    print()

    for index, relationship in enumerate(
        relationships,
        start=1,
    ):
        print(f"Relationship {index}")
        print(
            f"  Type:       {relationship.relationship_type}"
        )
        print(
            f"  Source:     {relationship.source_entity_id}"
        )
        print(
            f"  Target:     {relationship.target_entity_id}"
        )
        print(
            f"  Confidence: {relationship.confidence}"
        )
        print(
            f"  Evidence:   {relationship.evidence}"
        )
        print()

    db.commit()

    print("=" * 60)
    print("VERIFYING RETRIEVAL")
    print("=" * 60)

    saved_relationships = (
        service.get_for_organization(
            ORGANIZATION_ID
        )
    )

    print(
        f"RETRIEVED FROM DATABASE: "
        f"{len(saved_relationships)}"
    )

finally:
    db.close()