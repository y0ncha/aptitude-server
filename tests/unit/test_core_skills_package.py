"""Unit tests for the app.core.skills package layout."""

from __future__ import annotations

from importlib import import_module

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    ("module_name", "symbol_name"),
    [
        ("app.core.skills.discovery", "SkillDiscoveryService"),
        ("app.core.skills.exact_read", "enforce_and_audit_exact_read"),
        ("app.core.skills.fetch", "SkillFetchService"),
        ("app.core.skills.models", "SkillVersionDetail"),
        ("app.core.skills.projections", "to_skill_version_detail"),
        ("app.core.skills.registry", "SkillRegistryService"),
        ("app.core.skills.resolution", "SkillResolutionService"),
        ("app.core.skills.search", "SkillSearchService"),
    ],
)
def test_core_skills_modules_are_importable(module_name: str, symbol_name: str) -> None:
    module = import_module(module_name)

    assert hasattr(module, symbol_name)
