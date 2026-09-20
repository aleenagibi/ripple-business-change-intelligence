from uuid import UUID

from app.db.database import SessionLocal
from app.services.knowledge_graph_service import KnowledgeGraphService

ORGANIZATION_ID = UUID(
    "b5154ce1-c734-489e-a769-880535ceebcd"
)


def test_knowledge_graph_service() -> None:
    db = SessionLocal()

    try:
        service = KnowledgeGraphService(db)

        graph = service.build_for_organization(
            ORGANIZATION_ID
        )

        assert graph is not None
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0

        for node_id, data in graph.nodes(data=True):
            assert node_id is not None
            assert "name" in data
            assert "entity_type" in data

        for source, target, data in graph.edges(data=True):
            assert source in graph
            assert target in graph
            assert "relationship_type" in data
            assert "confidence" in data
            assert "evidence" in data

    finally:
        db.close()