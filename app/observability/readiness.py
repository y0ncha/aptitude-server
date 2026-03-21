"""Runtime readiness service and domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.ports import DatabaseReadinessPort


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """Represents a single dependency readiness check outcome."""

    name: str
    status: Literal["ok", "error"]
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Readiness result for the service and its dependencies."""

    status: Literal["ready", "not_ready"]
    checks: tuple[ReadinessCheck, ...]


class ReadinessService:
    """Compute service readiness based on infrastructure probes."""

    def __init__(self, database_probe: DatabaseReadinessPort) -> None:
        self._database_probe = database_probe

    def get_status(self) -> ReadinessReport:
        """Return readiness report for the current process state."""
        is_ready, detail = self._database_probe.ping()
        if is_ready:
            return ReadinessReport(
                status="ready",
                checks=(ReadinessCheck(name="database", status="ok"),),
            )

        return ReadinessReport(
            status="not_ready",
            checks=(ReadinessCheck(name="database", status="error", detail=detail),),
        )
