"""Prometheus-compatible process metrics."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram
from prometheus_client import generate_latest as prometheus_generate_latest

HTTP_DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
OPERATION_DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "aptitude_http_requests_total",
    "Total HTTP requests handled by the service.",
    labelnames=("method", "route", "status_class"),
    registry=REGISTRY,
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "aptitude_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "route"),
    buckets=HTTP_DURATION_BUCKETS,
    registry=REGISTRY,
)
REGISTRY_OPERATION_TOTAL = Counter(
    "aptitude_registry_operation_total",
    "Total registry operations by surface and outcome.",
    labelnames=("surface", "outcome"),
    registry=REGISTRY,
)
REGISTRY_OPERATION_DURATION_SECONDS = Histogram(
    "aptitude_registry_operation_duration_seconds",
    "Registry operation duration in seconds by surface.",
    labelnames=("surface",),
    buckets=OPERATION_DURATION_BUCKETS,
    registry=REGISTRY,
)
READINESS_STATUS = Gauge(
    "aptitude_readiness_status",
    "Readiness state for critical dependencies.",
    labelnames=("dependency",),
    registry=REGISTRY,
)

_ROUTE_TO_SURFACE: dict[tuple[str, str], str] = {
    ("POST", "/skills/{slug}/versions"): "publish",
    ("POST", "/discovery"): "discovery",
    ("GET", "/resolution/{slug}/{version}"): "resolution",
    ("GET", "/skills/{slug}/versions/{version}"): "metadata",
    ("GET", "/skills/{slug}/versions/{version}/content"): "content",
    ("PATCH", "/skills/{slug}/versions/{version}/status"): "lifecycle",
}


def observe_http_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record bounded HTTP and domain operation metrics."""
    normalized_method = method.upper()
    HTTP_REQUESTS_TOTAL.labels(
        method=normalized_method,
        route=route,
        status_class=_status_class(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=normalized_method,
        route=route,
    ).observe(duration_seconds)

    surface = _ROUTE_TO_SURFACE.get((normalized_method, route))
    if surface is None:
        return

    REGISTRY_OPERATION_TOTAL.labels(
        surface=surface,
        outcome=_outcome(status_code),
    ).inc()
    REGISTRY_OPERATION_DURATION_SECONDS.labels(surface=surface).observe(duration_seconds)


def set_database_readiness(*, is_ready: bool) -> None:
    """Track whether the primary database dependency is reachable."""
    READINESS_STATUS.labels(dependency="database").set(1 if is_ready else 0)


def generate_latest() -> bytes:
    """Return the current Prometheus exposition payload."""
    return prometheus_generate_latest(REGISTRY)


def metrics_content_type() -> str:
    """Return the Prometheus text exposition content type."""
    return CONTENT_TYPE_LATEST


def _status_class(status_code: int) -> str:
    return f"{status_code // 100}xx"


def _outcome(status_code: int) -> str:
    if status_code < 400:
        return "success"
    if status_code < 500:
        return "client_error"
    return "server_error"
