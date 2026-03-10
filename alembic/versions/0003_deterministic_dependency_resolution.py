"""Add dependency metadata edge read model.

Revision ID: 0003_deterministic_dependency_resolution
Revises: 0002_immutable_skill_registry
Create Date: 2026-03-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_deterministic_dependency_resolution"
down_revision = "0002_immutable_skill_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic's default version table uses VARCHAR(32), but this revision id is
    # longer and must fit before Alembic updates alembic_version after upgrade().
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    op.create_table(
        "skill_relationship_edges",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_skill_version_fk",
            sa.BigInteger(),
            sa.ForeignKey("skill_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_type", sa.Text(), nullable=False),
        sa.Column("target_skill_id", sa.Text(), nullable=False),
        sa.Column("target_version_selector", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "edge_type IN ('depends_on', 'extends')",
            name="ck_skill_relationship_edges_edge_type",
        ),
        sa.UniqueConstraint(
            "source_skill_version_fk",
            "edge_type",
            "target_skill_id",
            "target_version_selector",
            name="uq_skill_relationship_edges_source_type_target_selector",
        ),
    )
    op.create_index(
        "ix_skill_relationship_edges_source_edge_type",
        "skill_relationship_edges",
        ["source_skill_version_fk", "edge_type"],
    )
    op.create_index(
        "ix_skill_relationship_edges_target_skill_selector_edge_type",
        "skill_relationship_edges",
        ["target_skill_id", "target_version_selector", "edge_type"],
    )

    op.execute(
        """
        INSERT INTO skill_relationship_edges
            (source_skill_version_fk, edge_type, target_skill_id, target_version_selector)
        SELECT
            sv.id,
            'depends_on',
            edge ->> 'skill_id',
            COALESCE(edge ->> 'version', edge ->> 'version_constraint')
        FROM skill_versions AS sv
        CROSS JOIN LATERAL jsonb_array_elements(
            COALESCE(sv.manifest_json -> 'depends_on', '[]'::jsonb)
        ) AS edge
        WHERE edge ? 'skill_id'
          AND (edge ? 'version' OR edge ? 'version_constraint')
        ON CONFLICT ON CONSTRAINT uq_skill_relationship_edges_source_type_target_selector
        DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO skill_relationship_edges
            (source_skill_version_fk, edge_type, target_skill_id, target_version_selector)
        SELECT
            sv.id,
            'extends',
            edge ->> 'skill_id',
            edge ->> 'version'
        FROM skill_versions AS sv
        CROSS JOIN LATERAL jsonb_array_elements(
            COALESCE(sv.manifest_json -> 'extends', '[]'::jsonb)
        ) AS edge
        WHERE edge ? 'skill_id'
          AND edge ? 'version'
        ON CONFLICT ON CONSTRAINT uq_skill_relationship_edges_source_type_target_selector
        DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_skill_relationship_edges_target_skill_selector_edge_type",
        table_name="skill_relationship_edges",
    )
    op.drop_index(
        "ix_skill_relationship_edges_source_edge_type",
        table_name="skill_relationship_edges",
    )
    op.drop_table("skill_relationship_edges")
