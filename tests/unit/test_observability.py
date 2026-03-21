"""Unit tests for request-scoped observability helpers and metrics."""

from __future__ import annotations

import pytest
from prometheus_client import generate_latest

from app.core.metrics import REGISTRY
from app.core.observability import (
    clear_request_context,
    get_request_context,
    set_request_context,
)


@pytest.mark.unit
def test_request_context_round_trips_and_clears() -> None:
    clear_request_context()
    set_request_context(
        request_id="req-456",
        http_method="POST",
        http_route="/discovery",
        status_code=401,
        duration_ms=8.0,
    )

    context = get_request_context()
    assert context.request_id == "req-456"
    assert context.http_method == "POST"
    assert context.http_route == "/discovery"
    assert context.status_code == 401
    assert context.duration_ms == 8.0

    clear_request_context()
    cleared = get_request_context()
    assert cleared.request_id is None
    assert cleared.http_method is None
    assert cleared.http_route is None
    assert cleared.status_code is None
    assert cleared.duration_ms is None


@pytest.mark.unit
def test_metrics_registry_exposes_operability_series() -> None:
    payload = generate_latest(REGISTRY).decode("utf-8")

    assert "aptitude_http_requests_total" in payload
    assert "aptitude_http_request_duration_seconds" in payload
    assert "aptitude_registry_operation_total" in payload
    assert "aptitude_registry_operation_duration_seconds" in payload
    assert "aptitude_readiness_status" in payload
