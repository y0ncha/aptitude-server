"""Status-update SQLAlchemy mixin for immutable version lifecycle changes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy.exc import SQLAlchemyError

from app.core.governance import LifecycleStatus, TrustTier
from app.core.ports import AuditEventRecord, SkillRegistryPersistenceError, StoredSkillVersionStatus
from app.persistence.models.skill_search_document import SkillSearchDocument
from app.persistence.skill_registry_repository_base import SkillRegistryRepositoryBase


class SkillRegistryStatusMixin(SkillRegistryRepositoryBase):
    """Lifecycle update methods for immutable skill versions."""

    def update_version_status(
        self,
        *,
        slug: str,
        version: str,
        lifecycle_status: LifecycleStatus,
        audit_events: tuple[AuditEventRecord, ...] = (),
    ) -> StoredSkillVersionStatus | None:
        with self._session_factory() as session:
            try:
                entity = self._get_version_entity(session=session, slug=slug, version=version)
                if entity is None:
                    return None
                entity.lifecycle_status = lifecycle_status
                entity.lifecycle_changed_at = datetime.now(UTC)
                session.add(entity)
                session.flush()

                search_document = session.get(SkillSearchDocument, entity.id)
                if search_document is not None:
                    search_document.lifecycle_status = lifecycle_status
                    session.add(search_document)

                current_default_version_id = self._select_current_default_version_id(
                    session=session,
                    skill_id=entity.skill_fk,
                )
                self._add_audit_events(session=session, audit_events=audit_events)
                session.flush()
                session.commit()

                return StoredSkillVersionStatus(
                    slug=slug,
                    version=version,
                    lifecycle_status=cast(LifecycleStatus, entity.lifecycle_status),
                    trust_tier=cast(TrustTier, entity.trust_tier),
                    lifecycle_changed_at=entity.lifecycle_changed_at,
                    is_current_default=current_default_version_id == entity.id,
                )
            except SQLAlchemyError as exc:
                session.rollback()
                raise SkillRegistryPersistenceError(
                    "Failed to update immutable skill version status."
                ) from exc
