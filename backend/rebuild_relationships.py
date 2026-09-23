from uuid import UUID

from app.db.database import SessionLocal
from app.services.relationship_service import RelationshipService

ORGANIZATION_ID = UUID("90ddbf29-85e7-4322-8aed-b0ce88897cb1")

db = SessionLocal()

try:
    service = RelationshipService(db)
    relationships = service.process_organization(ORGANIZATION_ID)
    db.commit()

    print(f"Rebuilt relationships: {len(relationships)}")

    for relationship in relationships:
        print(
            f"{relationship.source_entity_id} "
            f"--[{relationship.relationship_type}]--> "
            f"{relationship.target_entity_id} "
            f"(confidence={relationship.confidence:.3f})"
        )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
