"""Reusable dependency declarations."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.readiness import ReadinessService
from app.core.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_readiness_service(request: Request) -> ReadinessService:
    """Return the process-scoped readiness service instance."""
    service = getattr(request.app.state, "readiness_service", None)
    if not isinstance(service, ReadinessService):
        raise RuntimeError("Readiness service is not initialized.")
    return service


ReadinessServiceDep = Annotated[ReadinessService, Depends(get_readiness_service)]
