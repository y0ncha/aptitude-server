"""Unit tests for skill manifest validation rules."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.interface.api.skills import SkillManifest, _validation_errors


@pytest.mark.unit
def test_skill_manifest_accepts_forward_compatible_relationship_fields() -> None:
    manifest = SkillManifest.model_validate(
        {
            "schema_version": "1.0",
            "skill_id": "python.lint",
            "version": "1.2.3",
            "name": "Python Lint",
            "description": "Linting skill",
            "tags": ["python", "lint"],
            "depends_on": [{"skill_id": "core.base", "version": "1.0.0"}],
            "extends": [{"skill_id": "python.base", "version": "2.0.0"}],
            "conflicts_with": [{"skill_id": "ruby.lint", "version": "1.0.0"}],
            "overlaps_with": [{"skill_id": "python.format", "version": "1.0.0"}],
        },
    )

    assert manifest.skill_id == "python.lint"
    assert manifest.version == "1.2.3"
    assert manifest.depends_on is not None
    assert manifest.depends_on[0].version == "1.0.0"


@pytest.mark.unit
def test_skill_manifest_accepts_dependency_constraints_and_optional_markers() -> None:
    manifest = SkillManifest.model_validate(
        {
            "schema_version": "1.0",
            "skill_id": "python.lint",
            "version": "1.2.3",
            "name": "Python Lint",
            "depends_on": [
                {
                    "skill_id": "core.base",
                    "version_constraint": ">=1.0.0,<2.0.0",
                    "optional": True,
                    "markers": ["linux", "gpu"],
                }
            ],
        },
    )

    assert manifest.depends_on is not None
    assert manifest.depends_on[0].version is None
    assert manifest.depends_on[0].version_constraint == ">=1.0.0,<2.0.0"
    assert manifest.depends_on[0].optional is True
    assert manifest.depends_on[0].markers == ["linux", "gpu"]


@pytest.mark.unit
def test_skill_manifest_rejects_ambiguous_dependency_version_selectors() -> None:
    with pytest.raises(ValidationError):
        SkillManifest.model_validate(
            {
                "schema_version": "1.0",
                "skill_id": "python.lint",
                "version": "1.2.3",
                "name": "Python Lint",
                "depends_on": [
                    {
                        "skill_id": "core.base",
                        "version": "1.0.0",
                        "version_constraint": ">=1.0.0,<2.0.0",
                    }
                ],
            },
        )


@pytest.mark.unit
def test_skill_manifest_rejects_invalid_dependency_constraint_syntax() -> None:
    with pytest.raises(ValidationError):
        SkillManifest.model_validate(
            {
                "schema_version": "1.0",
                "skill_id": "python.lint",
                "version": "1.2.3",
                "name": "Python Lint",
                "depends_on": [
                    {
                        "skill_id": "core.base",
                        "version_constraint": "latest",
                    }
                ],
            },
        )


@pytest.mark.unit
def test_validation_errors_for_dependency_declarations_are_json_serializable() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SkillManifest.model_validate(
            {
                "schema_version": "1.0",
                "skill_id": "python.lint",
                "version": "1.2.3",
                "name": "Python Lint",
                "depends_on": [{"skill_id": "core.base"}],
            },
        )

    errors = _validation_errors(exc_info.value)

    assert errors[0]["type"] == "value_error"
    assert "exactly one of `version` or `version_constraint`" in errors[0]["msg"]
    json.dumps({"errors": errors})


@pytest.mark.unit
def test_skill_manifest_rejects_non_semver_version() -> None:
    with pytest.raises(ValidationError):
        SkillManifest.model_validate(
            {
                "schema_version": "1.0",
                "skill_id": "python.lint",
                "version": "v1",
                "name": "Python Lint",
            },
        )


@pytest.mark.unit
def test_skill_manifest_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SkillManifest.model_validate(
            {
                "schema_version": "1.0",
                "skill_id": "python.lint",
                "version": "1.0.0",
                "name": "Python Lint",
                "extra_field": "not allowed",
            },
        )
