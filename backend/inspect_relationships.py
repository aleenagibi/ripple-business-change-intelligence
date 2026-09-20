from uuid import UUID

from app.db.database import SessionLocal
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship

ORGANIZATION_ID = UUID("b5154ce1-c734-489e-a769-880535ceebcd")

db = SessionLocal()

try:
    relationships = (
        db.query(EntityRelationship)
        .join(
            BusinessEntity,
            EntityRelationship.source_entity_id == BusinessEntity.id,
        )
        .all()
    )

    print(f"Total relationships: {len(relationships)}")
    print()

    for relationship in relationships:
        source = (
            db.query(BusinessEntity)
            .filter(BusinessEntity.id == relationship.source_entity_id)
            .first()
        )

        target = (
            db.query(BusinessEntity)
            .filter(BusinessEntity.id == relationship.target_entity_id)
            .first()
        )

        print(
            f"{source.name if source else relationship.source_entity_id}"
            f" --[{relationship.relationship_type}]--> "
            f"{target.name if target else relationship.target_entity_id}"
            f" | confidence={relationship.confidence:.3f}"
        )

finally:
    db.close()
