"""Shared session and helper logic for SQLAlchemy skill repository adapters."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload, selectinload, sessionmaker

from app.core.ports import AuditEventRecord, CreateSkillVersionRecord
from app.persistence.models.audit_event import AuditEvent
from app.persistence.models.skill import Skill
from app.persistence.models.skill_content import SkillContent
from app.persistence.models.skill_version import SkillVersion


class SkillRegistryRepositoryBase:
    """Shared SQLAlchemy session helpers for skill repository mixins."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _add_audit_events(
        *,
        session: Session,
        audit_events: tuple[AuditEventRecord, ...],
    ) -> None:
        if not audit_events:
            return
        session.add_all(
            AuditEvent(event_type=event.event_type, payload=event.payload) for event in audit_events
        )

    @staticmethod
    def _get_or_create_skill(*, session: Session, slug: str) -> Skill:
        existing = session.execute(select(Skill).where(Skill.slug == slug)).scalar_one_or_none()
        if existing is not None:
            return existing

        created = Skill(slug=slug)
        session.add(created)
        session.flush()
        return created

    @staticmethod
    def _get_or_create_content(
        *,
        session: Session,
        record: CreateSkillVersionRecord,
    ) -> SkillContent:
        existing = session.execute(
            select(SkillContent).where(
                SkillContent.checksum_digest == record.content.checksum_digest
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        created = SkillContent(
            raw_markdown=record.content.raw_markdown,
            storage_size_bytes=record.content.size_bytes,
            checksum_digest=record.content.checksum_digest,
        )
        session.add(created)
        session.flush()
        return created

    @staticmethod
    def _select_current_default_version_id(*, session: Session, skill_id: int) -> int | None:
        return session.execute(
            select(SkillVersion.id)
            .where(
                SkillVersion.skill_fk == skill_id,
                SkillVersion.lifecycle_status.in_(("published", "deprecated")),
            )
            .order_by(
                text(
                    "CASE skill_versions.lifecycle_status "
                    "WHEN 'published' THEN 0 WHEN 'deprecated' THEN 1 ELSE 2 END"
                ),
                SkillVersion.published_at.desc(),
                SkillVersion.id.desc(),
            )
            .limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def _get_version_entity(
        *,
        session: Session,
        slug: str,
        version: str,
    ) -> SkillVersion | None:
        statement = (
            select(SkillVersion)
            .join(Skill, Skill.id == SkillVersion.skill_fk)
            .options(
                joinedload(SkillVersion.skill),
                joinedload(SkillVersion.content),
                joinedload(SkillVersion.metadata_row),
                selectinload(SkillVersion.relationship_selectors),
            )
            .where(Skill.slug == slug, SkillVersion.version == version)
        )
        return session.execute(statement).scalar_one_or_none()
