from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    """Search request."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )

    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
    )


class RetrievalResult(BaseModel):
    """A ranked TF-IDF or dense retrieval result."""

    chunk_id: str
    chunk_index: int
    score: float
    content: str


class HybridRetrievalResult(BaseModel):
    """A hybrid retrieval result with ranking provenance."""

    chunk_id: str
    chunk_index: int
    score: float
    content: str
    tfidf_rank: int | None
    dense_rank: int | None


class ImpactAnalysisRequest(BaseModel):
    """Request for business impact analysis."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )

    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    max_distance: int = Field(
        default=3,
        ge=0,
        le=10,
    )

class ImpactSourceDocument(BaseModel):
    """A document containing evidence for an impacted business entity."""

    document_id: str
    filename: str
class ImpactAnalysisResult(BaseModel):
    """A business entity identified as potentially impacted."""

    entity_id: str
    name: str
    entity_type: str

    impact_score: float
    impact_level: str

    impact_origin: str
    impact_category: str

    semantic_relevance: float
    relationship_strength: float
    graph_proximity: float
    entity_importance: float
    propagation_distance: int

    path: list[str]
    explanation: str

    source_documents: list[ImpactSourceDocument]
