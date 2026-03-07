"""Reusable FastAPI dependencies for core services and settings.

This module centralizes dependency wiring for request handlers so interface code
can declare typed dependencies with minimal boilerplate.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.readiness import ReadinessService
from app.core.settings import Settings, get_settings
from app.core.skill_registry import SkillRegistryService

# Shared settings dependency used by route handlers and adapters.
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_readiness_service(request: Request) -> ReadinessService:
    """Return the process-scoped readiness service from app state.

    Raises:
        RuntimeError: If startup wiring did not initialize `readiness_service`.
    """
    service = getattr(request.app.state, "readiness_service", None)
    if not isinstance(service, ReadinessService):
        raise RuntimeError("Readiness service is not initialized.")
    return service


# Typed alias for injecting the readiness service via FastAPI dependencies.
ReadinessServiceDep = Annotated[ReadinessService, Depends(get_readiness_service)]


def get_skill_registry_service(request: Request) -> SkillRegistryService:
    """Return the immutable skill catalog service from app state.

    Raises:
        RuntimeError: If startup wiring did not initialize
            `skill_registry_service`.
    """
    service = getattr(request.app.state, "skill_registry_service", None)
    if not isinstance(service, SkillRegistryService):
        raise RuntimeError("Skill catalog service is not initialized.")
    return service


# Typed alias for injecting the skill catalog service in endpoint signatures.
SkillRegistryServiceDep = Annotated[SkillRegistryService, Depends(get_skill_registry_service)]
