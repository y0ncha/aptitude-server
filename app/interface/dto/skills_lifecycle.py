"""Lifecycle-surface DTOs for skill APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.governance import LifecycleStatus, TrustTier


class SkillVersionStatusUpdateRequest(BaseModel):
    """Lifecycle transition request for one immutable version."""

    status: LifecycleStatus
    note: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class SkillVersionStatusResponse(BaseModel):
    """Lifecycle status update response."""

    slug: str
    version: str
    status: LifecycleStatus
    trust_tier: TrustTier
    lifecycle_changed_at: datetime
    is_current_default: bool
