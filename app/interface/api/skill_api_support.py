"""Compatibility re-export for skill-related HTTP mappers."""

from __future__ import annotations

from pydantic import ValidationError

from app.interface.api.errors import serialize_validation_errors
from app.interface.api.skill_api_support_fetch import to_metadata_response
from app.interface.api.skill_api_support_lifecycle import to_version_status_response
from app.interface.api.skill_api_support_publish import to_create_command
from app.interface.api.skill_api_support_resolution import to_dependency_resolution_response

__all__ = [
    "to_create_command",
    "to_dependency_resolution_response",
    "to_metadata_response",
    "to_version_status_response",
    "validation_errors",
]


def validation_errors(exc: ValidationError) -> list[dict[str, object]]:
    """Return JSON-safe Pydantic validation details for the public error envelope."""
    return serialize_validation_errors(exc)
