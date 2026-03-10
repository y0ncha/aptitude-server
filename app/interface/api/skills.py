"""Compatibility router for publish/list plus legacy read endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Path, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.dependencies import (
    SkillDiscoveryServiceDep,
    SkillFetchServiceDep,
    SkillRegistryServiceDep,
)
from app.core.skill_registry import (
    ArtifactStorageFailureError,
    DuplicateSkillVersionError,
    IntegrityCheckFailedError,
    InvalidManifestError,
    SkillVersionNotFoundError,
)
from app.core.skill_search import SkillSearchQuery
from app.interface.api.errors import error_response
from app.interface.api.skill_api_support import (
    parse_manifest,
    to_detail_response,
    to_legacy_fetch_response,
    to_manifest_data,
    to_search_result_response,
    validation_errors,
)
from app.interface.dto.errors import ErrorEnvelope
from app.interface.dto.examples import (
    ARTIFACT_STORAGE_FAILURE_ERROR_EXAMPLE,
    DUPLICATE_SKILL_VERSION_ERROR_EXAMPLE,
    FETCH_SUCCESS_EXAMPLE,
    INTEGRITY_CHECK_FAILED_ERROR_EXAMPLE,
    INVALID_MANIFEST_ERROR_EXAMPLE,
    INVALID_REQUEST_ERROR_EXAMPLE,
    LIST_SUCCESS_EXAMPLE,
    PUBLISH_MULTIPART_FORM_EXAMPLE,
    PUBLISH_SUCCESS_EXAMPLE,
    SEARCH_INVALID_REQUEST_ERROR_EXAMPLE,
    SEARCH_SUCCESS_EXAMPLE,
    SKILL_VERSION_NOT_FOUND_ERROR_EXAMPLE,
)
from app.interface.dto.skills import (
    SEMVER_PATTERN,
    SKILL_ID_PATTERN,
    ArtifactMetadataResponse,
    ChecksumResponse,
    SkillManifest,
    SkillSearchRequest,
    SkillSearchResponse,
    SkillVersionDetailResponse,
    SkillVersionFetchResponse,
    SkillVersionListResponse,
    SkillVersionSummaryResponse,
)

router = APIRouter(tags=["skills"])

OpenAPIResponses = dict[int | str, dict[str, Any]]

REQUEST_VALIDATION_ERROR_RESPONSE: OpenAPIResponses = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorEnvelope,
        "description": (
            "The request payload, form fields, path parameters, or query parameters are invalid."
        ),
        "content": {"application/json": {"example": INVALID_REQUEST_ERROR_EXAMPLE}},
    }
}

PUBLISH_RESPONSES: OpenAPIResponses = {
    status.HTTP_201_CREATED: {
        "description": "Immutable skill version published successfully.",
        "content": {"application/json": {"example": PUBLISH_SUCCESS_EXAMPLE}},
    },
    status.HTTP_409_CONFLICT: {
        "model": ErrorEnvelope,
        "description": "The requested immutable `skill_id@version` already exists.",
        "content": {"application/json": {"example": DUPLICATE_SKILL_VERSION_ERROR_EXAMPLE}},
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorEnvelope,
        "description": "The request is invalid or the manifest JSON violates the publish contract.",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_request": {"value": INVALID_REQUEST_ERROR_EXAMPLE},
                    "invalid_manifest": {"value": INVALID_MANIFEST_ERROR_EXAMPLE},
                }
            }
        },
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorEnvelope,
        "description": "Artifact persistence failed while publishing the version.",
        "content": {"application/json": {"example": ARTIFACT_STORAGE_FAILURE_ERROR_EXAMPLE}},
    },
}

LIST_RESPONSES: OpenAPIResponses = {
    status.HTTP_200_OK: {
        "description": "Published versions listed successfully.",
        "content": {"application/json": {"example": LIST_SUCCESS_EXAMPLE}},
    },
    **REQUEST_VALIDATION_ERROR_RESPONSE,
}

LEGACY_SEARCH_RESPONSES: OpenAPIResponses = {
    status.HTTP_200_OK: {
        "description": "Compact advisory skill candidates returned successfully.",
        "content": {"application/json": {"example": SEARCH_SUCCESS_EXAMPLE}},
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorEnvelope,
        "description": "The search request is invalid.",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_request": {"value": INVALID_REQUEST_ERROR_EXAMPLE},
                    "missing_selector": {"value": SEARCH_INVALID_REQUEST_ERROR_EXAMPLE},
                }
            }
        },
    },
}

LEGACY_FETCH_RESPONSES: OpenAPIResponses = {
    status.HTTP_200_OK: {
        "description": "Immutable skill version fetched successfully.",
        "content": {"application/json": {"example": FETCH_SUCCESS_EXAMPLE}},
    },
    **REQUEST_VALIDATION_ERROR_RESPONSE,
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorEnvelope,
        "description": "The requested immutable `skill_id@version` does not exist.",
        "content": {"application/json": {"example": SKILL_VERSION_NOT_FOUND_ERROR_EXAMPLE}},
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorEnvelope,
        "description": "Artifact retrieval or integrity verification failed.",
        "content": {
            "application/json": {
                "examples": {
                    "integrity_check_failed": {"value": INTEGRITY_CHECK_FAILED_ERROR_EXAMPLE},
                    "artifact_storage_failure": {"value": ARTIFACT_STORAGE_FAILURE_ERROR_EXAMPLE},
                }
            }
        },
    },
}


@router.post(
    "/skills/publish",
    operation_id="publishSkillVersion",
    summary="Publish an immutable skill version",
    description=(
        "Accept multipart form data containing a JSON `manifest` string and a binary "
        "`artifact` upload. The manifest is validated at the API boundary, converted "
        "to core domain models, and persisted only if the same `skill_id@version` "
        "does not already exist."
    ),
    response_model=SkillVersionDetailResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
    responses=PUBLISH_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "examples": {
                        "publish": {
                            "summary": "Publish a new immutable skill version",
                            "value": PUBLISH_MULTIPART_FORM_EXAMPLE,
                        }
                    }
                }
            }
        }
    },
)
async def publish_skill_version(
    manifest: Annotated[
        str,
        Form(description="Manifest JSON string describing the immutable skill version."),
    ],
    artifact: Annotated[
        UploadFile,
        File(description="Binary artifact associated with the published version."),
    ],
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionDetailResponse | JSONResponse:
    """Publish immutable `skill@version` metadata and artifact."""
    try:
        parsed_manifest = parse_manifest(manifest)
        artifact_bytes = await artifact.read()
        stored = registry_service.publish_version(
            manifest=to_manifest_data(parsed_manifest),
            artifact_bytes=artifact_bytes,
        )
        return to_detail_response(stored=stored)
    except ValidationError as exc:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_MANIFEST",
            message="Manifest validation failed.",
            details={"errors": validation_errors(exc)},
        )
    except InvalidManifestError as exc:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_MANIFEST",
            message=str(exc),
        )
    except DuplicateSkillVersionError as exc:
        return error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_SKILL_VERSION",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )
    except ArtifactStorageFailureError as exc:
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="ARTIFACT_STORAGE_FAILURE",
            message=str(exc),
        )


@router.get(
    "/skills/search",
    operation_id="searchSkillsLegacy",
    summary="Search indexed skill metadata (legacy)",
    description=(
        "Legacy compatibility route for advisory discovery. New clients should call "
        "`GET /discovery/skills/search`. This route remains discovery-only and does "
        "not perform relationship resolution or dependency solving."
    ),
    response_model=SkillSearchResponse,
    response_model_exclude_unset=True,
    responses=LEGACY_SEARCH_RESPONSES,
    deprecated=True,
)
def search_skills_legacy(
    q: Annotated[str | None, Query(description="Full-text discovery query.")] = None,
    tag: Annotated[
        list[str] | None,
        Query(description="Repeatable tag filter; all values must match."),
    ] = None,
    language: Annotated[
        str | None,
        Query(description="Language alias filter implemented as a normalized tag."),
    ] = None,
    fresh_within_days: Annotated[
        int | None,
        Query(ge=0, description="Maximum age in days since publication."),
    ] = None,
    max_footprint_bytes: Annotated[
        int | None,
        Query(ge=0, description="Maximum allowed artifact size in bytes."),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum number of skill candidates to return."),
    ] = 20,
    discovery_service: SkillDiscoveryServiceDep = None,
) -> SkillSearchResponse | JSONResponse:
    """Compatibility wrapper for the legacy discovery route."""
    try:
        request = SkillSearchRequest(
            q=q,
            tags=tag or [],
            language=language,
            fresh_within_days=fresh_within_days,
            max_footprint_bytes=max_footprint_bytes,
            limit=limit,
        )
    except ValidationError as exc:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_REQUEST",
            message="Search request validation failed.",
            details={"errors": validation_errors(exc)},
        )

    results = discovery_service.search(
        query=SkillSearchQuery(
            q=request.q,
            tags=tuple(request.tags),
            language=request.language,
            fresh_within_days=request.fresh_within_days,
            max_footprint_bytes=request.max_footprint_bytes,
            limit=request.limit,
        )
    )
    return SkillSearchResponse(results=[to_search_result_response(item) for item in results])


@router.get(
    "/skills/{skill_id}/{version}",
    operation_id="getSkillVersionLegacy",
    summary="Fetch one immutable skill version (legacy)",
    description=(
        "Legacy compatibility route that returns metadata plus a base64-encoded artifact. "
        "New clients should use `GET /fetch/skills/{skill_id}/{version}` for metadata and "
        "`GET /fetch/skills/{skill_id}/{version}/artifact` for the binary payload."
    ),
    response_model=SkillVersionFetchResponse,
    response_model_exclude_unset=True,
    responses=LEGACY_FETCH_RESPONSES,
    deprecated=True,
)
def get_skill_version_legacy(
    skill_id: Annotated[
        str,
        Path(pattern=SKILL_ID_PATTERN, description="Stable identifier of the skill to fetch."),
    ],
    version: Annotated[
        str,
        Path(pattern=SEMVER_PATTERN, description="Exact immutable semantic version to fetch."),
    ],
    fetch_service: SkillFetchServiceDep,
) -> SkillVersionFetchResponse | JSONResponse:
    """Compatibility wrapper for the legacy combined exact fetch route."""
    try:
        stored = fetch_service.get_artifact(skill_id=skill_id, version=version)
        return to_legacy_fetch_response(stored=stored)
    except SkillVersionNotFoundError as exc:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SKILL_VERSION_NOT_FOUND",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )
    except IntegrityCheckFailedError as exc:
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTEGRITY_CHECK_FAILED",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )
    except ArtifactStorageFailureError as exc:
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="ARTIFACT_STORAGE_FAILURE",
            message=str(exc),
        )


@router.get(
    "/skills/{skill_id}",
    operation_id="listSkillVersions",
    summary="List published versions for a skill",
    description=(
        "Return every published immutable version for `skill_id`. Results are "
        "deterministic and ordered newest-first by publication timestamp."
    ),
    response_model=SkillVersionListResponse,
    response_model_exclude_unset=True,
    responses=LIST_RESPONSES,
)
def list_skill_versions(
    skill_id: Annotated[
        str,
        Path(
            pattern=SKILL_ID_PATTERN,
            description="Stable identifier of the skill whose versions should be listed.",
        ),
    ],
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionListResponse:
    """List immutable versions for a skill in deterministic order."""
    versions = registry_service.list_versions(skill_id=skill_id)
    return SkillVersionListResponse(
        skill_id=skill_id,
        versions=[
            SkillVersionSummaryResponse(
                skill_id=item.skill_id,
                version=item.version,
                manifest=SkillManifest.model_validate(item.manifest_json),
                checksum=ChecksumResponse(
                    algorithm=item.checksum.algorithm,
                    digest=item.checksum.digest,
                ),
                artifact_metadata=ArtifactMetadataResponse(
                    relative_path=item.artifact.relative_path,
                    size_bytes=item.artifact.size_bytes,
                ),
                published_at=item.published_at,
            )
            for item in versions
        ],
    )


def _validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    """Backward-compatible helper retained for tests and legacy imports."""
    return validation_errors(exc)
