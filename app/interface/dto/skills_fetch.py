"""Exact-fetch DTOs for skill APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.governance import LifecycleStatus, TrustTier
from app.interface.dto.skills_shared import (
    ChecksumResponse,
    ProvenanceResponse,
    SkillContentSummaryResponse,
    SkillMetadataResponse,
)


class SkillVersionMetadataResponse(BaseModel):
    """Immutable metadata envelope returned by publish and exact metadata fetch."""

    slug: str
    version: str
    version_checksum: ChecksumResponse
    content: SkillContentSummaryResponse
    metadata: SkillMetadataResponse
    lifecycle_status: LifecycleStatus
    trust_tier: TrustTier
    provenance: ProvenanceResponse | None = None
    published_at: datetime
