"""Typed relationship edges between immutable skill versions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.models.base import Base


class SkillRelationshipEdge(Base):
    """Represents a typed relationship edge from one skill version to another."""

    __tablename__ = "skill_relationship_edges"
    __table_args__ = (
        CheckConstraint(
            "edge_type IN ('depends_on', 'extends')",
            name="ck_skill_relationship_edges_edge_type",
        ),
        Index(
            "ix_skill_relationship_edges_source_edge_type",
            "source_skill_version_fk",
            "edge_type",
        ),
        Index(
            "ix_skill_relationship_edges_target_skill_selector_edge_type",
            "target_skill_id",
            "target_version_selector",
            "edge_type",
        ),
        Index(
            "uq_skill_relationship_edges_source_type_target_selector",
            "source_skill_version_fk",
            "edge_type",
            "target_skill_id",
            "target_version_selector",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_skill_version_fk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("skill_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_version_selector: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
