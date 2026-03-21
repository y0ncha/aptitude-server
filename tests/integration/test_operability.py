"""Integration coverage for metrics, request correlation, and audit stitching."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from alembic import command
from app.main import create_app


@pytest.fixture
def migrated_registry_database(clean_integration_database: str) -> str:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", clean_integration_database)
    command.upgrade(config, "head")
    return clean_integration_database


def _headers(token: str, *, request_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    return headers


def _request(version: str) -> dict[str, object]:
    return {
        "intent": "create_skill",
        "version": version,
        "content": {"raw_markdown": "# Python Lint\n\nLint Python files.\n"},
        "metadata": {
            "name": "Python Lint",
            "description": "Linting skill",
            "tags": ["python", "lint"],
            "headers": {"runtime": "python"},
            "inputs_schema": {"type": "object"},
            "outputs_schema": {"type": "object"},
            "token_estimate": 128,
            "maturity_score": 0.9,
            "security_score": 0.95,
        },
        "governance": {"trust_tier": "untrusted", "provenance": None},
        "relationships": {
            "depends_on": [],
            "extends": [],
            "conflicts_with": [],
            "overlaps_with": [],
        },
    }


def _query_audit_events(database_url: str) -> list[dict[str, Any]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return [
                {"event_type": str(row["event_type"]), "payload": row["payload"]}
                for row in connection.execute(
                    text("SELECT event_type, payload FROM audit_events ORDER BY id")
                ).mappings()
            ]
    finally:
        engine.dispose()


@pytest.mark.integration
def test_metrics_endpoint_is_unauthenticated_and_exposes_prometheus_payload(
    monkeypatch: pytest.MonkeyPatch,
    require_integration_database: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", require_integration_database)

    with TestClient(create_app()) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "aptitude_http_requests_total" in response.text


@pytest.mark.integration
def test_request_id_is_echoed_on_success_and_error_responses(
    monkeypatch: pytest.MonkeyPatch,
    require_integration_database: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", require_integration_database)

    with TestClient(create_app()) as client:
        success = client.get("/healthz", headers={"X-Request-ID": "req-health"})
        error = client.post(
            "/discovery",
            json={"name": "Python Lint"},
            headers={"X-Request-ID": "req-error"},
        )

    assert success.status_code == 200
    assert success.headers["X-Request-ID"] == "req-health"
    assert error.status_code == 401
    assert error.headers["X-Request-ID"] == "req-error"


@pytest.mark.integration
def test_publish_flow_stitches_request_id_into_audit_rows_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
    migrated_registry_database: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_registry_database)
    slug = f"python.operability.{uuid4().hex}"

    with TestClient(create_app()) as client:
        publish = client.post(
            f"/skills/{slug}/versions",
            json=_request("1.0.0"),
            headers=_headers("publisher-token", request_id="req-publish"),
        )
        metrics = client.get("/metrics")

    audit_events = _query_audit_events(migrated_registry_database)

    assert publish.status_code == 201, publish.text
    assert publish.headers["X-Request-ID"] == "req-publish"
    assert any(
        event["payload"] is not None and event["payload"].get("request_id") == "req-publish"
        for event in audit_events
    )
    assert "aptitude_registry_operation_total" in metrics.text
