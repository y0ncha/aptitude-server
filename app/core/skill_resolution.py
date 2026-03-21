"""Core exact dependency-resolution service for immutable skill versions."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exact_read_support import ExactReadAuditInfo, enforce_and_audit_exact_read
from app.core.governance import CallerIdentity, GovernancePolicy
from app.core.ports import AuditPort, ExactSkillCoordinate, SkillRelationshipReadPort
from app.core.skill_models import SkillRelationshipSelector, SkillVersionNotFoundError


@dataclass(frozen=True, slots=True)
class ResolvedSkillDependencies:
    """Direct authored dependency selectors for one immutable skill version."""

    slug: str
    version: str
    depends_on: tuple[SkillRelationshipSelector, ...]


class SkillResolutionService:
    """Read-only exact dependency service with no solving behavior."""

    def __init__(
        self,
        *,
        relationship_reader: SkillRelationshipReadPort,
        audit_recorder: AuditPort,
        governance_policy: GovernancePolicy,
    ) -> None:
        self._relationship_reader = relationship_reader
        self._audit_recorder = audit_recorder
        self._governance_policy = governance_policy

    def get_direct_dependencies(
        self,
        *,
        caller: CallerIdentity,
        slug: str,
        version: str,
    ) -> ResolvedSkillDependencies:
        """Return authored direct `depends_on` selectors for one exact version."""
        coordinate = ExactSkillCoordinate(slug=slug, version=version)
        stored_sources = self._relationship_reader.get_relationship_sources_batch(
            coordinates=(coordinate,),
        )
        if not stored_sources:
            raise SkillVersionNotFoundError(slug=slug, version=version)

        stored = stored_sources[0]
        enforce_and_audit_exact_read(
            caller=caller,
            governance_policy=self._governance_policy,
            audit_recorder=self._audit_recorder,
            audit_info=ExactReadAuditInfo(
                slug=stored.slug,
                version=stored.version,
                lifecycle_status=stored.lifecycle_status,
                trust_tier=stored.trust_tier,
            ),
            surface="resolution",
        )

        resolved = ResolvedSkillDependencies(
            slug=stored.slug,
            version=stored.version,
            depends_on=tuple(
                SkillRelationshipSelector(
                    slug=selector.slug,
                    version=selector.version,
                    version_constraint=selector.version_constraint,
                    optional=selector.optional,
                    markers=selector.markers,
                )
                for selector in stored.relationships
                if selector.edge_type == "depends_on"
            ),
        )
        return resolved
