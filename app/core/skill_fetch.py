"""Core exact fetch service for immutable metadata and markdown reads."""

from __future__ import annotations

from app.core.exact_read_support import ExactReadAuditInfo, enforce_and_audit_exact_read
from app.core.governance import CallerIdentity, GovernancePolicy
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
            surface="metadata",
        )
        detail = to_skill_version_detail(stored=stored)
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
            surface="content",
        )
        document = SkillContentDocument(
            raw_markdown=stored.raw_markdown,
            checksum=SkillChecksum(
                algorithm=SHA256_ALGORITHM,
                digest=stored.checksum_digest,
            ),
            size_bytes=stored.size_bytes,
        )
        return document
