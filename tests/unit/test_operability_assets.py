"""Unit tests for local observability assets."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_prometheus_and_grafana_assets_exist() -> None:
    assert (REPO_ROOT / "ops/monitoring/prometheus/prometheus.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/prometheus/alerts.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/otel-lgtm/otelcol-config.yaml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/provisioning/datasources/prometheus.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/provisioning/datasources/loki.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/provisioning/dashboards/dashboards.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/dashboards").exists()


@pytest.mark.unit
def test_prometheus_scrape_config_targets_metrics_endpoint() -> None:
    document = (REPO_ROOT / "ops/monitoring/prometheus/prometheus.yml").read_text()

    assert "/metrics" in document
    assert "aptitude-server" in document
    assert "127.0.0.1:9090" in document
    assert "job_name: loki" in document
    assert "job_name: otelcol" in document
    assert "127.0.0.1:8888" in document
    assert "rule_files" in document


@pytest.mark.unit
def test_grafana_dashboard_covers_key_registry_surfaces() -> None:
    dashboards = sorted((REPO_ROOT / "ops/monitoring/grafana/dashboards").glob("*.json"))

    assert len(dashboards) >= 2
    metrics_dashboard = next(
        dashboard
        for dashboard in dashboards
        if dashboard.name == "aptitude-server-operability.json"
    )
    logs_dashboard = next(
        dashboard for dashboard in dashboards if dashboard.name == "aptitude-server-logs.json"
    )

    metrics_document = metrics_dashboard.read_text()
    assert "aptitude_http_requests_total" in metrics_document
    assert "aptitude_http_request_duration_seconds" in metrics_document
    assert "publish" in metrics_document
    assert "discovery" in metrics_document
    assert "resolution" in metrics_document
    assert "metadata" in metrics_document
    assert "content" in metrics_document
    assert "lifecycle" in metrics_document
    assert '"uid": "prometheus"' in metrics_document

    logs_document = logs_dashboard.read_text()
    assert '"uid": "loki"' in logs_document
    assert "request_id" in logs_document
    assert "event_type" in logs_document
    assert "service_name" in logs_document
    assert "aptitude-server" in logs_document
    assert "line_format" in logs_document
    assert "http_route" in logs_document
    assert "duration_ms" in logs_document


@pytest.mark.unit
def test_grafana_datasources_define_stable_uids() -> None:
    prometheus_document = (
        REPO_ROOT / "ops/monitoring/grafana/provisioning/datasources/prometheus.yml"
    ).read_text()
    loki_document = (
        REPO_ROOT / "ops/monitoring/grafana/provisioning/datasources/loki.yml"
    ).read_text()

    assert "uid: prometheus" in prometheus_document
    assert "uid: loki" in loki_document
    assert "127.0.0.1:9090" in prometheus_document
    assert "127.0.0.1:3100" in loki_document


@pytest.mark.unit
def test_prometheus_alert_rules_cover_log_pipeline_health() -> None:
    document = (REPO_ROOT / "ops/monitoring/prometheus/alerts.yml").read_text()

    assert "AptitudeServerLokiUnavailable" in document
    assert "AptitudeServerCollectorUnavailable" in document


@pytest.mark.unit
def test_observability_compose_profile_uses_single_otel_lgtm_container() -> None:
    document = (REPO_ROOT / "docker-compose.yml").read_text()

    assert "grafana/otel-lgtm" in document
    assert "otelcol-config.yaml" in document
    assert "aptitude-observability" in document
    assert "http://127.0.0.1:8000/readyz" in document
