"""Lifecycle-surface API mappers."""

from __future__ import annotations

from app.core.skills.models import SkillVersionStatusUpdate
from app.interface.dto.skills_lifecycle import SkillVersionStatusResponse


def to_version_status_response(update: SkillVersionStatusUpdate) -> SkillVersionStatusResponse:
    """Convert a core lifecycle update result into the public schema."""
    return SkillVersionStatusResponse(
        slug=update.slug,
        version=update.version,
        status=update.status,
        trust_tier=update.trust_tier,
        lifecycle_changed_at=update.lifecycle_changed_at,
        is_current_default=update.is_current_default,
    )
