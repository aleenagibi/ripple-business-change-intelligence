from uuid import UUID

from app.db.database import SessionLocal
from app.repositories.relationship_repository import RelationshipRepository
from app.repositories.entity_repository import EntityRepository
from app.services.knowledge_graph_service import KnowledgeGraphService

ORGANIZATION_ID = UUID("b5154ce1-c734-489e-a769-880535ceebcd")

db = SessionLocal()

try:
    relationship_repo = RelationshipRepository(db)
    entity_repo = EntityRepository(db)
    graph_service = KnowledgeGraphService(db)

    relationships = relationship_repo.list_for_organization(ORGANIZATION_ID)

    print("RELATIONSHIPS FROM REPOSITORY:", len(relationships))

    for r in relationships:
        print(
            r.relationship_type,
            r.source_entity_id,
            "->",
            r.target_entity_id,
            "confidence=",
            r.confidence,
        )

    graph = graph_service.build_for_organization(ORGANIZATION_ID)

    print()
    print("GRAPH NODES:", graph.number_of_nodes())
    print("GRAPH EDGES:", graph.number_of_edges())

    for source, target, data in graph.edges(data=True):
        print(
            data.get("relationship_type"),
            source,
            "->",
            target,
        )

finally:
    db.close()
