"""Unit tests for local observability assets."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_prometheus_and_grafana_assets_exist() -> None:
    assert (REPO_ROOT / "ops/monitoring/prometheus/prometheus.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/prometheus/alerts.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/provisioning/datasources/prometheus.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/provisioning/dashboards/dashboards.yml").exists()
    assert (REPO_ROOT / "ops/monitoring/grafana/dashboards").exists()


@pytest.mark.unit
def test_prometheus_scrape_config_targets_metrics_endpoint() -> None:
    document = (REPO_ROOT / "ops/monitoring/prometheus/prometheus.yml").read_text()

    assert "/metrics" in document
    assert "aptitude-server" in document
    assert "rule_files" in document


@pytest.mark.unit
def test_grafana_dashboard_covers_key_registry_surfaces() -> None:
    dashboards = sorted((REPO_ROOT / "ops/monitoring/grafana/dashboards").glob("*.json"))

    assert dashboards
    document = dashboards[0].read_text()
    assert "publish" in document
    assert "discovery" in document
    assert "resolution" in document
    assert "metadata" in document
    assert "content" in document
    assert "lifecycle" in document
