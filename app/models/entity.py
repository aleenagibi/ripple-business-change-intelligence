import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.canonical_entity import CanonicalEntity
    from app.models.chunk import DocumentChunk
    from app.models.entity_relationship import EntityRelationship


class BusinessEntity(Base):
    """A business concept or artifact extracted from a document chunk."""

    __tablename__ = "business_entities"

    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "normalized_name",
            "entity_type",
            name="uq_chunk_entity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_chunks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    canonical_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "canonical_entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    canonical_entity: Mapped["CanonicalEntity"] = relationship(
        "CanonicalEntity",
        back_populates="mentions",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk",
        back_populates="entities",
    )
    outgoing_relationships: Mapped[
        list["EntityRelationship"]
    ] = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )

    incoming_relationships: Mapped[
        list["EntityRelationship"]
    ] = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )