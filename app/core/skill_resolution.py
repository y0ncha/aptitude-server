"""Core exact dependency-resolution service for immutable skill versions."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.audit_events import build_exact_read_audit_event, build_exact_read_denied_audit_event
from app.core.governance import CallerIdentity, GovernancePolicy, PolicyViolation
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
        try:
            self._governance_policy.ensure_exact_read_allowed(
                caller=caller,
                lifecycle_status=stored.lifecycle_status,
            )
        except PolicyViolation as exc:
            denied_event = build_exact_read_denied_audit_event(
                caller=caller,
                slug=stored.slug,
                version=stored.version,
                lifecycle_status=stored.lifecycle_status,
                trust_tier=stored.trust_tier,
                surface="resolution",
                policy_profile=self._governance_policy.profile_name,
                reason_code=exc.code,
            )
            self._audit_recorder.record_event(
                event_type=denied_event.event_type,
                payload=denied_event.payload,
            )
            raise

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
        event = build_exact_read_audit_event(
            caller=caller,
            slug=stored.slug,
            version=stored.version,
            lifecycle_status=stored.lifecycle_status,
            trust_tier=stored.trust_tier,
            surface="resolution",
            policy_profile=self._governance_policy.profile_name,
        )
        self._audit_recorder.record_event(event_type=event.event_type, payload=event.payload)
        return resolved
