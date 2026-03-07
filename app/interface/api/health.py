"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.core.dependencies import ReadinessServiceDep, SettingsDep

router = APIRouter(tags=["health"])


class HealthzResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    environment: str


class ReadinessCheck(BaseModel):
    name: str
    status: Literal["ok", "error"]
    detail: str | None = None


class ReadyzResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: list[ReadinessCheck]


@router.get("/healthz", response_model=HealthzResponse)
def get_healthz(settings: SettingsDep) -> HealthzResponse:
    """Return process liveness for lightweight probes."""
    return HealthzResponse(service=settings.app_name, environment=settings.app_env)


@router.get("/readyz", response_model=ReadyzResponse)
def get_readyz(response: Response, readiness_service: ReadinessServiceDep) -> ReadyzResponse:
    """Return dependency readiness, including a database connectivity check."""
    readiness_report = readiness_service.get_status()
    checks = [
        ReadinessCheck(name=check.name, status=check.status, detail=check.detail)
        for check in readiness_report.checks
    ]
    if readiness_report.status == "ready":
        return ReadyzResponse(status="ready", checks=checks)

    response.status_code = 503
    return ReadyzResponse(status="not_ready", checks=checks)
