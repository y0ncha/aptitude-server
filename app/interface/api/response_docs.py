"""Shared OpenAPI response fragments for the public HTTP contract."""

from __future__ import annotations

from typing import Any

from fastapi import status

from app.interface.dto.errors import ErrorEnvelope
from app.interface.dto.examples import (
    INVALID_REQUEST_ERROR_EXAMPLE,
    SKILL_VERSION_NOT_FOUND_ERROR_EXAMPLE,
)

ApiResponses = dict[int | str, dict[str, Any]]


def invalid_request_response(*, description: str) -> ApiResponses:
    """Return the shared 422 response fragment used by contract routes."""
    return {
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorEnvelope,
            "description": description,
            "content": {"application/json": {"example": INVALID_REQUEST_ERROR_EXAMPLE}},
        }
    }


def skill_version_not_found_response(*, description: str) -> ApiResponses:
    """Return the shared exact-version 404 response fragment."""
    return {
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorEnvelope,
            "description": description,
            "content": {"application/json": {"example": SKILL_VERSION_NOT_FOUND_ERROR_EXAMPLE}},
        }
    }
