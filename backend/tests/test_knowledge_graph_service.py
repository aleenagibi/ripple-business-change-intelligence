import uuid

from app.db.database import SessionLocal
from app.models.canonical_entity import CanonicalEntity
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.entity import BusinessEntity
from app.models.entity_relationship import EntityRelationship
from app.models.organization import Organization
from app.services.knowledge_graph_service import KnowledgeGraphService


def test_knowledge_graph_service() -> None:
    db = SessionLocal()

    organization = Organization(
        name="Knowledge Graph Test Organization",
        slug=f"knowledge-graph-test-{uuid.uuid4().hex}",
    )
    db.add(organization)
    db.flush()

    document = Document(
        id=uuid.uuid4(),
        organization_id=organization.id,
        filename="knowledge_graph_test.txt",
        document_type="txt",
        mime_type="text/plain",
        storage_path="test/knowledge_graph_test.txt",
        extracted_text=(
            "The Payment API uses the Payment Gateway."
        ),
        processing_status="completed",
        document_metadata={"test": True},
    )
    db.add(document)
    db.flush()

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        chunk_index=0,
        content="The Payment API uses the Payment Gateway.",
        token_count=8,
    )
    db.add(chunk)
    db.flush()

    payment_api = CanonicalEntity(
        id=uuid.uuid4(),
        organization_id=organization.id,
        name="Payment API",
        normalized_name="payment api",
        entity_type="API",
        description="Payment processing API.",
    )

    payment_gateway = CanonicalEntity(
        id=uuid.uuid4(),
        organization_id=organization.id,
        name="Payment Gateway",
        normalized_name="payment gateway",
        entity_type="SYSTEM",
        description="Payment gateway system.",
    )

    db.add_all([payment_api, payment_gateway])
    db.flush()

    payment_api_mention = BusinessEntity(
        id=uuid.uuid4(),
        chunk_id=chunk.id,
        name="Payment API",
        normalized_name="payment api",
        entity_type="API",
        canonical_entity_id=payment_api.id,
    )

    payment_gateway_mention = BusinessEntity(
        id=uuid.uuid4(),
        chunk_id=chunk.id,
        name="Payment Gateway",
        normalized_name="payment gateway",
        entity_type="SYSTEM",
        canonical_entity_id=payment_gateway.id,
    )

    db.add_all([
        payment_api_mention,
        payment_gateway_mention,
    ])
    db.flush()

    relationship = EntityRelationship(
        id=uuid.uuid4(),
        source_entity_id=payment_api_mention.id,
        target_entity_id=payment_gateway_mention.id,
        relationship_type="USES",
        confidence=0.95,
        evidence_chunk_id=chunk.id,
        evidence="The Payment API uses the Payment Gateway.",
    )

    db.add(relationship)
    db.commit()

    try:
        service = KnowledgeGraphService(db)

        graph = service.build_for_organization(
            organization.id
        )

        assert graph is not None
        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1

        assert payment_api.id in graph
        assert payment_gateway.id in graph

        edge_data = graph.get_edge_data(
            payment_api.id,
            payment_gateway.id,
        )

        assert edge_data is not None

        edge = next(iter(edge_data.values()))

        assert edge["relationship_type"] == "USES"
        assert edge["confidence"] == 0.95
        assert (
            edge["evidence"]
            == "The Payment API uses the Payment Gateway."
        )

        for node_id, data in graph.nodes(data=True):
            assert node_id is not None
            assert "name" in data
            assert "entity_type" in data

    finally:
        db.delete(organization)
        db.commit()
        db.close()