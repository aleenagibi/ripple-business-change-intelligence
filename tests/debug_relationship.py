from app.db.database import SessionLocal
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.entity_repository import EntityRepository

ORGANIZATION_ID = "b5154ce1-c734-489e-a769-880535ceebcd"


db = SessionLocal()

try:
    chunk_repository = ChunkRepository(db)
    entity_repository = EntityRepository(db)

    chunks = chunk_repository.list_for_organization(
        ORGANIZATION_ID
    )

    print("=" * 60)
    print("RELATIONSHIP DEBUG")
    print("=" * 60)

    print(f"CHUNKS: {len(chunks)}")
    print()

    total_entities = 0

    for index, chunk in enumerate(chunks, start=1):
        entities = entity_repository.list_for_chunk(
            chunk.id
        )

        total_entities += len(entities)

        print(f"CHUNK {index}")
        print(f"ID: {chunk.id}")
        print(f"ENTITIES: {len(entities)}")
        print(f"CONTENT: {chunk.content[:300]}")
        print()

        for entity in entities:
            print(
                f"  {entity.name} | "
                f"{entity.entity_type} | "
                f"{entity.id}"
            )

        print("-" * 60)

    print()
    print(f"TOTAL ENTITIES: {total_entities}")
    print("=" * 60)

finally:
    db.close()