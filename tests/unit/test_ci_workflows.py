"""Regression coverage for CI workflow database orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
@pytest.mark.parametrize(
    "workflow_path",
    [
        ".github/workflows/main-ci.yml",
        ".github/workflows/dev-ci.yml",
    ],
)
def test_ci_workflows_boot_runner_tests_from_compose_db(workflow_path: str) -> None:
    document = (REPO_ROOT / workflow_path).read_text()

    assert "services:" not in document
    assert "docker compose up -d db" in document
    assert "docker compose exec -T db pg_isready -U postgres -d aptitude" in document
