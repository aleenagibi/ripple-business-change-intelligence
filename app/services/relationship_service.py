from uuid import UUID

from app.engines.relationship_extraction_engine import (
    ExtractedRelationship,
    RelationshipExtractionEngine,
)
from app.models.chunk import DocumentChunk
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.entity_repository import EntityRepository
from app.repositories.relationship_repository import RelationshipRepository
from sqlalchemy.orm import Session


class RelationshipService:
    """Discovers and persists relationships between business entity mentions."""

    def __init__(self, db: Session) -> None:
        self.db = db

        self.chunk_repository = ChunkRepository(db)
        self.entity_repository = EntityRepository(db)
        self.repository = RelationshipRepository(db)

        self.engine = RelationshipExtractionEngine()

    def process_organization(
        self,
        organization_id: UUID,
    ) -> list[EntityRelationship]:
        """
        Discover relationships across all chunks and persist them
        between extracted business entity mentions.
        """

        chunks = self.chunk_repository.list_for_organization(
            organization_id
        )

        if not chunks:
            return []

        self.repository.delete_for_organization(
            organization_id
        )

        relationship_map: dict[
            tuple[UUID, UUID, str],
            EntityRelationship,
        ] = {}

        for chunk in chunks:
            entities = self.entity_repository.list_for_chunk(
                chunk.id
            )

            if len(entities) < 2:
                continue

            extracted = self.engine.extract(
                entities=entities,
                text=chunk.content,
            )

            for relationship in extracted:
                model = self._build_model(
                    relationship=relationship,
                    entities=entities,
                    chunk=chunk,
                )

                if model is None:
                    continue

                key = (
                    model.source_entity_id,
                    model.target_entity_id,
                    model.relationship_type,
                )

                existing = relationship_map.get(key)

                if existing is None:
                    relationship_map[key] = model
                elif model.confidence > existing.confidence:
                    relationship_map[key] = model

        relationships = list(relationship_map.values())

        if relationships:
            self.repository.add_many(relationships)
            self.db.flush()

        return relationships

    @staticmethod
    def _build_model(
        relationship: ExtractedRelationship,
        entities: list[BusinessEntity],
        chunk: DocumentChunk,
    ) -> EntityRelationship | None:
        """Convert an extracted relationship into a persisted relationship."""

        entity_by_id = {
            entity.id: entity
            for entity in entities
        }

        try:
            source_id = UUID(
                relationship.source_entity_id
            )
            target_id = UUID(
                relationship.target_entity_id
            )
        except (TypeError, ValueError):
            return None

        source = entity_by_id.get(source_id)
        target = entity_by_id.get(target_id)

        if source is None or target is None:
            return None

        if source.id == target.id:
            return None

        return EntityRelationship(
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type=(
                relationship.relationship_type
                .strip()
                .upper()
            ),
            confidence=relationship.confidence,
            evidence_chunk_id=chunk.id,
            evidence=relationship.evidence,
        )

    def get_for_organization(
        self,
        organization_id: UUID,
    ) -> list[EntityRelationship]:
        """Retrieve all persisted relationships for an organization."""

        return self.repository.list_for_organization(
            organization_id
        )