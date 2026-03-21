"""Read-side SQLAlchemy mixin for exact version and relationship reads."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select, tuple_
from sqlalchemy.orm import joinedload, selectinload

from app.core.governance import LifecycleStatus, TrustTier
from app.core.ports import (
    ExactSkillCoordinate,
    StoredSkillRelationshipSource,
    StoredSkillVersion,
    StoredSkillVersionContent,
)
from app.persistence.models.skill import Skill
from app.persistence.models.skill_version import SkillVersion
from app.persistence.skill_registry_repository_base import SkillRegistryRepositoryBase
from app.persistence.skill_registry_repository_support import (
    sort_relationship_selectors,
    to_stored_selector,
    to_stored_skill_version,
)


class SkillRegistryReadMixin(SkillRegistryRepositoryBase):
    """Read-side methods for exact version and relationship retrieval."""

    def get_version(self, *, slug: str, version: str) -> StoredSkillVersion | None:
        with self._session_factory() as session:
            entity = self._get_version_entity(session=session, slug=slug, version=version)
            if entity is None:
                return None
            return to_stored_skill_version(entity)

    def get_version_content(
        self,
        *,
        slug: str,
        version: str,
    ) -> StoredSkillVersionContent | None:
        with self._session_factory() as session:
            statement = (
                select(SkillVersion)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .options(
                    joinedload(SkillVersion.skill),
                    joinedload(SkillVersion.content),
                )
                .where(Skill.slug == slug, SkillVersion.version == version)
            )
            item = session.execute(statement).scalar_one_or_none()
            if item is None:
                return None
            return StoredSkillVersionContent(
                slug=item.skill.slug,
                version=item.version,
                raw_markdown=item.content.raw_markdown,
                checksum_digest=item.content.checksum_digest,
                size_bytes=item.content.storage_size_bytes,
                lifecycle_status=cast(LifecycleStatus, item.lifecycle_status),
                trust_tier=cast(TrustTier, item.trust_tier),
            )

    def get_relationship_sources_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillRelationshipSource, ...]:
        if not coordinates:
            return ()

        coordinate_pairs = [(item.slug, item.version) for item in coordinates]
        with self._session_factory() as session:
            statement = (
                select(SkillVersion)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .options(
                    joinedload(SkillVersion.skill),
                    selectinload(SkillVersion.relationship_selectors),
                )
                .where(tuple_(Skill.slug, SkillVersion.version).in_(coordinate_pairs))
            )
            rows = session.execute(statement).scalars().all()
            return tuple(
                StoredSkillRelationshipSource(
                    slug=item.skill.slug,
                    version=item.version,
                    lifecycle_status=cast(LifecycleStatus, item.lifecycle_status),
                    trust_tier=cast(TrustTier, item.trust_tier),
                    relationships=tuple(
                        to_stored_selector(selector)
                        for selector in sort_relationship_selectors(item.relationship_selectors)
                    ),
                )
                for item in rows
            )
