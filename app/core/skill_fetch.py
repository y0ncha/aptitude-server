"""Core exact fetch service for immutable metadata and markdown reads."""

from __future__ import annotations

from app.core.audit_events import build_exact_read_audit_event, build_exact_read_denied_audit_event
from app.core.governance import CallerIdentity, GovernancePolicy, PolicyViolation
from app.core.ports import AuditPort, SkillVersionReadPort
from app.core.skill_models import (
    SHA256_ALGORITHM,
    SkillChecksum,
    SkillContentDocument,
    SkillVersionDetail,
    SkillVersionNotFoundError,
)
from app.core.skill_version_projections import to_skill_version_detail


class SkillFetchService:
    """Read-only service for exact immutable metadata and markdown access."""

    def __init__(
        self,
        *,
        version_reader: SkillVersionReadPort,
        audit_recorder: AuditPort,
        governance_policy: GovernancePolicy,
    ) -> None:
        self._version_reader = version_reader
        self._audit_recorder = audit_recorder
        self._governance_policy = governance_policy

    def get_version_metadata(
        self,
        *,
        caller: CallerIdentity,
        slug: str,
        version: str,
    ) -> SkillVersionDetail:
        """Return immutable version metadata for one exact coordinate."""
        stored = self._version_reader.get_version(slug=slug, version=version)
        if stored is None:
            raise SkillVersionNotFoundError(slug=slug, version=version)

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
                surface="metadata",
                policy_profile=self._governance_policy.profile_name,
                reason_code=exc.code,
            )
            self._audit_recorder.record_event(
                event_type=denied_event.event_type,
                payload=denied_event.payload,
            )
            raise
        detail = to_skill_version_detail(stored=stored)
        event = build_exact_read_audit_event(
            caller=caller,
            slug=stored.slug,
            version=stored.version,
            lifecycle_status=stored.lifecycle_status,
            trust_tier=stored.trust_tier,
            surface="metadata",
            policy_profile=self._governance_policy.profile_name,
        )
        self._audit_recorder.record_event(event_type=event.event_type, payload=event.payload)
        return detail

    def get_content(
        self,
        *,
        caller: CallerIdentity,
        slug: str,
        version: str,
    ) -> SkillContentDocument:
        """Return immutable markdown content for one exact coordinate."""
        stored = self._version_reader.get_version_content(slug=slug, version=version)
        if stored is None:
            raise SkillVersionNotFoundError(slug=slug, version=version)

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
                surface="content",
                policy_profile=self._governance_policy.profile_name,
                reason_code=exc.code,
            )
            self._audit_recorder.record_event(
                event_type=denied_event.event_type,
                payload=denied_event.payload,
            )
            raise
        document = SkillContentDocument(
            raw_markdown=stored.raw_markdown,
            checksum=SkillChecksum(
                algorithm=SHA256_ALGORITHM,
                digest=stored.checksum_digest,
            ),
            size_bytes=stored.size_bytes,
        )
        event = build_exact_read_audit_event(
            caller=caller,
            slug=stored.slug,
            version=stored.version,
            lifecycle_status=stored.lifecycle_status,
            trust_tier=stored.trust_tier,
            surface="content",
            policy_profile=self._governance_policy.profile_name,
        )
        self._audit_recorder.record_event(event_type=event.event_type, payload=event.payload)
        return document
