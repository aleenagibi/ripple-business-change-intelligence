"""add canonical entities

Revision ID: cd4972f4bf5b
Revises: 977fdef6f3a1
Create Date: 2026-08-29 10:22:30.516494
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cd4972f4bf5b"
down_revision: Union[str, Sequence[str], None] = "977fdef6f3a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create canonical entities and migrate existing entity mentions."""

    # ---------------------------------------------------------
    # 1. Create canonical_entities table
    # ---------------------------------------------------------

    op.create_table(
        "canonical_entities",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "normalized_name",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "normalized_name",
            "entity_type",
            name="uq_organization_canonical_entity",
        ),
    )

    op.create_index(
        "ix_canonical_entities_organization_id",
        "canonical_entities",
        ["organization_id"],
    )

    op.create_index(
        "ix_canonical_entities_normalized_name",
        "canonical_entities",
        ["normalized_name"],
    )

    op.create_index(
        "ix_canonical_entities_entity_type",
        "canonical_entities",
        ["entity_type"],
    )

    # ---------------------------------------------------------
    # 2. Add canonical_entity_id to existing business_entities
    #
    # It MUST initially be nullable because existing rows
    # already exist.
    # ---------------------------------------------------------

    op.add_column(
        "business_entities",
        sa.Column(
            "canonical_entity_id",
            sa.UUID(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_business_entities_canonical_entity_id",
        "business_entities",
        ["canonical_entity_id"],
    )

    # ---------------------------------------------------------
    # 3. Create one canonical entity for every unique
    #    organization + normalized_name + entity_type
    # ---------------------------------------------------------

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO canonical_entities (
                id,
                organization_id,
                name,
                normalized_name,
                entity_type,
                description
            )
            SELECT
                gen_random_uuid(),
                d.organization_id,
                MIN(be.name),
                be.normalized_name,
                be.entity_type,
                MIN(be.description)
            FROM business_entities AS be
            JOIN document_chunks AS dc
                ON dc.id = be.chunk_id
            JOIN documents AS d
                ON d.id = dc.document_id
            GROUP BY
                d.organization_id,
                be.normalized_name,
                be.entity_type
            """
        )
    )

    # ---------------------------------------------------------
    # 4. Connect every existing BusinessEntity mention
    #    to its canonical entity.
    # ---------------------------------------------------------

    connection.execute(
        sa.text(
            """
            UPDATE business_entities AS be
            SET canonical_entity_id = ce.id
            FROM document_chunks AS dc,
                documents AS d,
                canonical_entities AS ce
            WHERE dc.id = be.chunk_id
            AND d.id = dc.document_id
            AND ce.organization_id = d.organization_id
            AND ce.normalized_name = be.normalized_name
            AND ce.entity_type = be.entity_type
            """
        )
    )

    # ---------------------------------------------------------
    # 5. Add the foreign key after the data has been populated.
    # ---------------------------------------------------------

    op.create_foreign_key(
        "fk_business_entities_canonical_entity_id",
        "business_entities",
        "canonical_entities",
        ["canonical_entity_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ---------------------------------------------------------
    # 6. Existing rows are now guaranteed to have a canonical
    #    entity, so make the column mandatory.
    # ---------------------------------------------------------

    op.alter_column(
        "business_entities",
        "canonical_entity_id",
        existing_type=sa.UUID(),
        nullable=False,
    )


def downgrade() -> None:
    """Remove canonical entity support."""

    op.drop_constraint(
        "fk_business_entities_canonical_entity_id",
        "business_entities",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_business_entities_canonical_entity_id",
        table_name="business_entities",
    )

    op.drop_column(
        "business_entities",
        "canonical_entity_id",
    )

    op.drop_index(
        "ix_canonical_entities_entity_type",
        table_name="canonical_entities",
    )

    op.drop_index(
        "ix_canonical_entities_normalized_name",
        table_name="canonical_entities",
    )

    op.drop_index(
        "ix_canonical_entities_organization_id",
        table_name="canonical_entities",
    )

    op.drop_table("canonical_entities")