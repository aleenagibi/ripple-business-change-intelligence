from uuid import UUID

from sqlalchemy.orm import Session

from app.engines.canonical_resolution_engine import (
    CanonicalResolutionEngine,
)
from app.engines.entity_extraction_engine import (
    EntityExtractionEngine,
)
from app.models.canonical_entity import CanonicalEntity
from app.models.chunk import DocumentChunk
from app.models.entity import BusinessEntity
from app.repositories.entity_repository import EntityRepository


class EntityService:
    """Extracts and persists business entities from document chunks."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = EntityRepository(db)
        self.engine = EntityExtractionEngine()
        self.canonical_resolution_engine = (
            CanonicalResolutionEngine()
        )

    def process_chunk(
        self,
        chunk: DocumentChunk,
        canonical_entities: list[CanonicalEntity] | None = None,
    ) -> list[BusinessEntity]:
        """
        Extract entities from one chunk and resolve them
        to organization-level canonical entities.

        Resolution strategy:

            1. Exact normalized-name match using an in-memory lookup.
            2. Semantic match against existing canonical entities
               of the same entity type.
            3. Create a new canonical entity when no safe match exists.

        Existing entity occurrences for the chunk are removed
        before new occurrences are inserted.
        """

        # ---------------------------------------------------------
        # 1. Remove entities previously extracted for this chunk.
        # ---------------------------------------------------------

        self.repository.delete_for_chunk(chunk.id)

        self.db.flush()

        # ---------------------------------------------------------
        # 2. Extract entities from chunk content.
        # ---------------------------------------------------------

        extracted = self.engine.extract(
            chunk.content
        )

        organization_id = chunk.document.organization_id

        entities: list[BusinessEntity] = []

        # ---------------------------------------------------------
        # 3. Load canonical candidates once when not supplied.
        # ---------------------------------------------------------

        if canonical_entities is None:
            canonical_entities = (
                self.repository.list_canonical_entities(
                    organization_id
                )
            )

        # ---------------------------------------------------------
        # 4. Build an in-memory exact-match lookup.
        #
        # Key:
        #     (normalized_name, entity_type)
        #
        # This avoids a database query for every extracted entity.
        # ---------------------------------------------------------

        canonical_lookup: dict[
            tuple[str, str],
            CanonicalEntity,
        ] = {
            (
                canonical.normalized_name.strip().lower(),
                canonical.entity_type.strip().upper(),
            ): canonical
            for canonical in canonical_entities
        }
        # ---------------------------------------------------------
        # 5. Deduplicate entities within this chunk.
        # ---------------------------------------------------------
        seen_entities: set[tuple[str, str]] = set()

        for entity in extracted:

            normalized_name = (
                entity.normalized_name.strip().lower()
            )

            entity_type = (
                entity.entity_type.strip().upper()
            )

            if not normalized_name or not entity_type:
                continue

            entity_key = (
                normalized_name,
                entity_type,
            )

            if entity_key in seen_entities:
                continue

            seen_entities.add(entity_key)

            # -----------------------------------------------------
            # 6. Exact canonical lookup in memory.
            # -----------------------------------------------------

            canonical_entity = canonical_lookup.get(
                entity_key
            )

            # -----------------------------------------------------
            # 7. If exact matching fails, perform semantic
            #    canonical resolution.
            # -----------------------------------------------------

            if canonical_entity is None:

                semantic_match = (
                    self.canonical_resolution_engine.find_best_match(
                        name=entity.name,
                        entity_type=entity_type,
                        candidates=canonical_entities,
                    )
                )

                if semantic_match is not None:
                    canonical_entity = next(
                        (
                            candidate
                            for candidate in canonical_entities
                            if str(candidate.id)
                            == semantic_match.entity_id
                        ),
                        None,
                    )

            # -----------------------------------------------------
            # 8. Create a new canonical entity when no safe
            #    existing match is found.
            # -----------------------------------------------------

            if canonical_entity is None:

                canonical_entity = CanonicalEntity(
                    organization_id=organization_id,
                    name=entity.name,
                    normalized_name=normalized_name,
                    entity_type=entity_type,
                    description=entity.description,
                )

                self.repository.add_canonical_entity(
                    canonical_entity
                )

                canonical_entities.append(
                    canonical_entity
                )

                # Make the new entity immediately available for
                # exact matching later in this processing run.
                canonical_lookup[entity_key] = (
                    canonical_entity
                )

            # -----------------------------------------------------
            # 9. Enrich an existing canonical entity if necessary.
            # -----------------------------------------------------

            elif (
                not canonical_entity.description
                and entity.description
            ):
                canonical_entity.description = (
                    entity.description
                )

            # -----------------------------------------------------
            # 10. Create chunk-level business entity occurrence.
            # -----------------------------------------------------

            business_entity = BusinessEntity(
                chunk_id=chunk.id,
                canonical_entity_id=canonical_entity.id,
                name=entity.name,
                normalized_name=normalized_name,
                entity_type=entity_type,
                description=entity.description,
            )

            entities.append(
                business_entity
            )

        # ---------------------------------------------------------
        # 11. Persist all entity occurrences.
        # ---------------------------------------------------------

        self.repository.add_many(
            entities
        )

        self.db.flush()

        return entities

    def process_organization(
        self,
        organization_id: UUID,
    ) -> list[BusinessEntity]:
        """
        Extract and persist entities for every document chunk
        belonging to an organization.

        Canonical entities are loaded once and reused across all
        chunks to avoid repeated database queries.
        """

        chunks = (
            self.repository.list_chunks_for_organization(
                organization_id
            )
        )

        if not chunks:
            return []

        # Load the organization's canonical vocabulary once.
        canonical_entities = (
            self.repository.list_canonical_entities(
                organization_id
            )
        )

        entities: list[BusinessEntity] = []

        for chunk in chunks:

            extracted_entities = self.process_chunk(
                chunk=chunk,
                canonical_entities=canonical_entities,
            )

            entities.extend(
                extracted_entities
            )

        return entities