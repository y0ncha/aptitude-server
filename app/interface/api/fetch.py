"""HTTP contract for exact immutable metadata and artifact fetch endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Response, status
from fastapi.responses import JSONResponse

from app.core.dependencies import SkillFetchServiceDep
from app.core.ports import ExactSkillCoordinate
from app.core.skill_fetch import SkillFetchBatchItem
from app.core.skill_registry import (
    ArtifactStorageFailureError,
    IntegrityCheckFailedError,
    SkillVersionNotFoundError,
)
from app.interface.api.errors import error_response
from app.interface.api.skill_api_support import artifact_download_path, to_exact_version_response
from app.interface.dto.errors import ErrorEnvelope
from app.interface.dto.examples import (
    ARTIFACT_STORAGE_FAILURE_ERROR_EXAMPLE,
    EXACT_FETCH_SUCCESS_EXAMPLE,
    FETCH_BATCH_SUCCESS_EXAMPLE,
    INTEGRITY_CHECK_FAILED_ERROR_EXAMPLE,
    INVALID_REQUEST_ERROR_EXAMPLE,
    SKILL_VERSION_NOT_FOUND_ERROR_EXAMPLE,
)
from app.interface.dto.skills import (
    SEMVER_PATTERN,
    SKILL_ID_PATTERN,
    ExactSkillCoordinateRequest,
    ExactSkillVersionResponse,
    SkillFetchBatchItemResponse,
    SkillFetchBatchRequest,
    SkillFetchBatchResponse,
)

router = APIRouter(tags=["fetch"])

OpenAPIResponses = dict[int | str, dict[str, Any]]

REQUEST_VALIDATION_ERROR_RESPONSE: OpenAPIResponses = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorEnvelope,
        "description": "The request body or path parameters are invalid.",
        "content": {"application/json": {"example": INVALID_REQUEST_ERROR_EXAMPLE}},
    }
}

FETCH_RESPONSES: OpenAPIResponses = {
    status.HTTP_200_OK: {
        "description": "Exact immutable skill version metadata returned successfully.",
        "content": {"application/json": {"example": EXACT_FETCH_SUCCESS_EXAMPLE}},
    },
    **REQUEST_VALIDATION_ERROR_RESPONSE,
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorEnvelope,
        "description": "The requested immutable `skill_id@version` does not exist.",
        "content": {"application/json": {"example": SKILL_VERSION_NOT_FOUND_ERROR_EXAMPLE}},
    },
}

BATCH_FETCH_RESPONSES: OpenAPIResponses = {
    status.HTTP_200_OK: {
        "description": "Ordered exact immutable metadata results returned successfully.",
        "content": {"application/json": {"example": FETCH_BATCH_SUCCESS_EXAMPLE}},
    },
    **REQUEST_VALIDATION_ERROR_RESPONSE,
}

ARTIFACT_FETCH_RESPONSES: OpenAPIResponses = {
    status.HTTP_200_OK: {
        "description": "Immutable artifact bytes streamed successfully.",
        "content": {"application/octet-stream": {}},
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


@router.get(
    "/fetch/skills/{skill_id}/{version}",
    operation_id="getExactSkillVersionMetadata",
    summary="Fetch exact immutable version metadata",
    description=(
        "Return the stored manifest, checksum, and a backend-agnostic artifact reference for "
        "one exact immutable skill version. This route does not inline artifact bytes."
    ),
    response_model=ExactSkillVersionResponse,
    response_model_exclude_unset=True,
    responses=FETCH_RESPONSES,
)
def get_skill_version_metadata(
    skill_id: Annotated[
        str,
        Path(pattern=SKILL_ID_PATTERN, description="Stable identifier of the skill to fetch."),
    ],
    version: Annotated[
        str,
        Path(pattern=SEMVER_PATTERN, description="Exact immutable semantic version to fetch."),
    ],
    fetch_service: SkillFetchServiceDep,
) -> ExactSkillVersionResponse | JSONResponse:
    """Fetch one immutable version metadata projection without artifact bytes."""
    try:
        stored = fetch_service.get_version_metadata(skill_id=skill_id, version=version)
        return to_exact_version_response(
            stored=stored,
            download_path=artifact_download_path(skill_id=skill_id, version=version),
        )
    except SkillVersionNotFoundError as exc:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SKILL_VERSION_NOT_FOUND",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )


@router.post(
    "/fetch/skill-versions:batch",
    operation_id="batchGetExactSkillVersionMetadata",
    summary="Batch fetch exact immutable version metadata",
    description=(
        "Return ordered exact immutable version metadata results for up to 100 requested "
        "coordinates. Each result is independent and preserves the original request order."
    ),
    response_model=SkillFetchBatchResponse,
    response_model_exclude_unset=True,
    responses=BATCH_FETCH_RESPONSES,
)
def batch_get_skill_version_metadata(
    request: SkillFetchBatchRequest,
    fetch_service: SkillFetchServiceDep,
) -> SkillFetchBatchResponse:
    """Fetch exact immutable version metadata in request order."""
    results = fetch_service.get_version_metadata_batch(
        coordinates=tuple(
            ExactSkillCoordinate(skill_id=item.skill_id, version=item.version)
            for item in request.coordinates
        )
    )
    return SkillFetchBatchResponse(
        results=[_to_fetch_batch_item_response(item) for item in results]
    )


@router.get(
    "/fetch/skills/{skill_id}/{version}/artifact",
    operation_id="streamExactSkillArtifact",
    summary="Stream one immutable artifact",
    description=(
        "Stream the immutable artifact bytes for one exact `skill_id@version`. The service "
        "verifies checksum integrity before returning the payload."
    ),
    response_model=None,
    responses=ARTIFACT_FETCH_RESPONSES,
)
def get_skill_artifact(
    skill_id: Annotated[
        str,
        Path(pattern=SKILL_ID_PATTERN, description="Stable identifier of the skill to fetch."),
    ],
    version: Annotated[
        str,
        Path(pattern=SEMVER_PATTERN, description="Exact immutable semantic version to fetch."),
    ],
    fetch_service: SkillFetchServiceDep,
) -> Response | JSONResponse:
    """Stream one exact immutable artifact after integrity verification."""
    try:
        stored = fetch_service.get_artifact(skill_id=skill_id, version=version)
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

    return Response(
        content=stored.artifact_bytes or b"",
        media_type="application/octet-stream",
        headers={
            "ETag": stored.checksum.digest,
            "Cache-Control": "public, immutable",
            "Content-Length": str(stored.artifact.size_bytes),
        },
    )


def _to_fetch_batch_item_response(item: SkillFetchBatchItem) -> SkillFetchBatchItemResponse:
    if item.version is None:
        return SkillFetchBatchItemResponse(
            status="not_found",
            coordinate=ExactSkillCoordinateRequest(
                skill_id=item.coordinate.skill_id,
                version=item.coordinate.version,
            ),
            version=None,
        )

    return SkillFetchBatchItemResponse(
        status="found",
        coordinate=ExactSkillCoordinateRequest(
            skill_id=item.coordinate.skill_id,
            version=item.coordinate.version,
        ),
        version=to_exact_version_response(
            stored=item.version,
            download_path=artifact_download_path(
                skill_id=item.coordinate.skill_id,
                version=item.coordinate.version,
            ),
        ),
    )
