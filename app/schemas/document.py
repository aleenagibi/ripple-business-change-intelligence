from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Document returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    filename: str
    document_type: str
    mime_type: str
    processing_status: str
    created_at: datetime


class DocumentIndexStats(BaseModel):
    """Derived Ripple indexing statistics for a document."""

    file_size_bytes: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    entity_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    retrieval_method: str


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response including Ripple indexing statistics."""

    index_stats: DocumentIndexStats
