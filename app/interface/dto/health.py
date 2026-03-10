"""Health endpoint DTOs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


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
