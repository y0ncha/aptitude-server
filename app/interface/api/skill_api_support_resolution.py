"""Resolution-surface API mappers."""

from __future__ import annotations

from app.core.skill_resolution import ResolvedSkillDependencies
from app.interface.dto.skills_resolution import (
    DependencySelectorResponse,
    SkillDependencyResolutionResponse,
)


def to_dependency_resolution_response(
    resolved: ResolvedSkillDependencies,
) -> SkillDependencyResolutionResponse:
    """Convert resolved dependencies into the public response payload."""
    return SkillDependencyResolutionResponse(
        slug=resolved.slug,
        version=resolved.version,
        depends_on=[
            DependencySelectorResponse(
                slug=item.slug,
                version=item.version,
                version_constraint=item.version_constraint,
                optional=item.optional,
                markers=list(item.markers),
            )
            for item in resolved.depends_on
        ],
    )
