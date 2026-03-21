"""Write-side SQLAlchemy mixin for immutable skill persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.ports import (
    AuditEventRecord,
    CreateSkillVersionRecord,
    SkillRegistryPersistenceError,
    StoredSkillVersion,
)
from app.core.skill_registry import DuplicateSkillVersionError
from app.persistence.models.skill import Skill
from app.persistence.models.skill_metadata import SkillMetadata
from app.persistence.models.skill_relationship_selector import SkillRelationshipSelector
from app.persistence.models.skill_version import SkillVersion
from app.persistence.skill_registry_repository_base import SkillRegistryRepositoryBase
from app.persistence.skill_registry_repository_support import (
    build_search_document,
    is_duplicate_skill_version_error,
    to_stored_skill_version,
)


class SkillRegistryWriteMixin(SkillRegistryRepositoryBase):
    """Write-side methods for immutable skill publish behavior."""

    def skill_exists(self, *, slug: str) -> bool:
        with self._session_factory() as session:
            statement = select(Skill.id).where(Skill.slug == slug).limit(1)
            return session.execute(statement).scalar_one_or_none() is not None

    def version_exists(self, *, slug: str, version: str) -> bool:
        with self._session_factory() as session:
            statement = (
                select(SkillVersion.id)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .where(Skill.slug == slug, SkillVersion.version == version)
                .limit(1)
            )
            return session.execute(statement).scalar_one_or_none() is not None

    def create_version(
        self,
        *,
        record: CreateSkillVersionRecord,
        audit_events: tuple[AuditEventRecord, ...] = (),
    ) -> StoredSkillVersion:
        with self._session_factory() as session:
            try:
                skill = self._get_or_create_skill(session=session, slug=record.slug)
                content = self._get_or_create_content(session=session, record=record)
                metadata = SkillMetadata(
                    name=record.metadata.name,
                    description=record.metadata.description,
                    tags=list(record.metadata.tags),
                    headers=record.metadata.headers,
                    inputs_schema=record.metadata.inputs_schema,
                    outputs_schema=record.metadata.outputs_schema,
                    token_estimate=record.metadata.token_estimate,
                    maturity_score=record.metadata.maturity_score,
                    security_score=record.metadata.security_score,
                )
                session.add(metadata)
                session.flush()

                skill_version = SkillVersion(
                    skill_fk=skill.id,
                    version=record.version,
                    content_fk=content.id,
                    metadata_fk=metadata.id,
                    checksum_digest=record.version_checksum_digest,
                    lifecycle_status="published",
                    lifecycle_changed_at=datetime.now(UTC),
                    trust_tier=record.governance.trust_tier,
                    provenance_repo_url=(
                        None
                        if record.governance.provenance is None
                        else record.governance.provenance.repo_url
                    ),
                    provenance_commit_sha=(
                        None
                        if record.governance.provenance is None
                        else record.governance.provenance.commit_sha
                    ),
                    provenance_tree_path=(
                        None
                        if record.governance.provenance is None
                        else record.governance.provenance.tree_path
                    ),
                    provenance_publisher_identity=(
                        None
                        if record.governance.provenance is None
                        else record.governance.provenance.publisher_identity
                    ),
                    policy_profile_at_publish=(
                        None
                        if record.governance.provenance is None
                        else record.governance.provenance.policy_profile
                    ),
                )
                session.add(skill_version)
                session.flush()
                session.refresh(
                    skill_version,
                    attribute_names=["published_at", "created_at", "lifecycle_changed_at"],
                )

                selector_rows = [
                    SkillRelationshipSelector(
                        source_skill_version_fk=skill_version.id,
                        edge_type=item.edge_type,
                        ordinal=item.ordinal,
                        target_slug=item.slug,
                        target_version=item.version,
                        version_constraint=item.version_constraint,
                        optional=item.optional,
                        markers=list(item.markers),
                    )
                    for item in record.relationships
                ]
                session.add_all(selector_rows)
                session.flush()
                session.add(
                    build_search_document(
                        skill_version_id=skill_version.id,
                        slug=record.slug,
                        version=record.version,
                        metadata=record.metadata,
                        governance=record.governance,
                        published_at=skill_version.published_at,
                        content_size_bytes=record.content.size_bytes,
                    )
                )
                self._add_audit_events(session=session, audit_events=audit_events)
                session.commit()

                reloaded = self._get_version_entity(
                    session=session, slug=record.slug, version=record.version
                )
                if reloaded is None:
                    raise SkillRegistryPersistenceError(
                        "Created skill version could not be reloaded."
                    )
                return to_stored_skill_version(reloaded)
            except IntegrityError as exc:
                session.rollback()
                if is_duplicate_skill_version_error(exc):
                    raise DuplicateSkillVersionError(
                        slug=record.slug,
                        version=record.version,
                    ) from exc
                raise SkillRegistryPersistenceError(
                    "Failed to persist immutable skill version."
                ) from exc
            except SQLAlchemyError as exc:
                session.rollback()
                raise SkillRegistryPersistenceError(
                    "Failed to persist immutable skill version."
                ) from exc
