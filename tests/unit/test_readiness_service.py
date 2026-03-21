"""Unit tests for core readiness service behavior."""

from __future__ import annotations

import pytest

from app.observability.readiness import ReadinessService


class HealthyProbe:
    """Probe stub for healthy database readiness."""

    def ping(self) -> tuple[bool, str | None]:
        return True, None


class UnhealthyProbe:
    """Probe stub for unhealthy database readiness."""

    def ping(self) -> tuple[bool, str | None]:
        return False, "connection refused"


@pytest.mark.unit
def test_readiness_service_returns_ready_when_probe_succeeds() -> None:
    service = ReadinessService(database_probe=HealthyProbe())

    report = service.get_status()

    assert report.status == "ready"
    assert report.checks[0].name == "database"
    assert report.checks[0].status == "ok"
    assert report.checks[0].detail is None


@pytest.mark.unit
def test_readiness_service_returns_not_ready_when_probe_fails() -> None:
    service = ReadinessService(database_probe=UnhealthyProbe())

    report = service.get_status()

    assert report.status == "not_ready"
    assert report.checks[0].name == "database"
    assert report.checks[0].status == "error"
    assert report.checks[0].detail == "connection refused"
