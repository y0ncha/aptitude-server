"""Immutable skill catalog API endpoints."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Path, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.dependencies import SkillRegistryServiceDep
from app.core.skill_registry import (
    ArtifactStorageFailureError,
    DuplicateSkillVersionError,
    IntegrityCheckFailedError,
    InvalidManifestError,
    SkillManifestData,
    SkillRelationshipRef,
    SkillVersionDetail,
    SkillVersionNotFoundError,
)

SEMVER_PATTERN = (
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
SKILL_ID_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,127})$"

router = APIRouter(tags=["skills"])


class RelationshipRef(BaseModel):
    """Typed manifest reference to another immutable skill version."""

    skill_id: str = Field(min_length=1, max_length=128, pattern=SKILL_ID_PATTERN)
    version: str = Field(pattern=SEMVER_PATTERN)

    model_config = ConfigDict(extra="forbid")


class SkillManifest(BaseModel):
    """Validated immutable skill manifest contract."""

    schema_version: str = Field(default="1.0", min_length=1, max_length=20)
    skill_id: str = Field(min_length=1, max_length=128, pattern=SKILL_ID_PATTERN)
    version: str = Field(pattern=SEMVER_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    depends_on: list[RelationshipRef] | None = None
    extends: list[RelationshipRef] | None = None
    conflicts_with: list[RelationshipRef] | None = None
    overlaps_with: list[RelationshipRef] | None = None

    model_config = ConfigDict(extra="forbid")


class ErrorBody(BaseModel):
    """Error detail object for API error envelope."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    """Standardized error envelope for milestone 02 endpoints."""

    error: ErrorBody


class ChecksumResponse(BaseModel):
    algorithm: str
    digest: str


class ArtifactMetadataResponse(BaseModel):
    relative_path: str
    size_bytes: int


class SkillVersionDetailResponse(BaseModel):
    skill_id: str
    version: str
    manifest: SkillManifest
    checksum: ChecksumResponse
    artifact_metadata: ArtifactMetadataResponse
    published_at: datetime


class SkillVersionFetchResponse(SkillVersionDetailResponse):
    artifact_base64: str


class SkillVersionSummaryResponse(BaseModel):
    skill_id: str
    version: str
    manifest: SkillManifest
    checksum: ChecksumResponse
    artifact_metadata: ArtifactMetadataResponse
    published_at: datetime


class SkillVersionListResponse(BaseModel):
    skill_id: str
    versions: list[SkillVersionSummaryResponse]


@router.post(
    "/skills/publish",
    response_model=SkillVersionDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_skill_version(
    manifest: Annotated[str, Form()],
    artifact: Annotated[UploadFile, File()],
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionDetailResponse | JSONResponse:
    """Publish immutable `skill@version` metadata and artifact."""
    return await _publish_from_payload(
        manifest=manifest,
        artifact=artifact,
        registry_service=registry_service,
    )


async def _publish_from_payload(
    *,
    manifest: str,
    artifact: UploadFile,
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionDetailResponse | JSONResponse:
    """Validate publish payload, enforce immutability, and persist the version."""
    try:
        parsed_manifest = _parse_manifest(manifest)
        artifact_bytes = await artifact.read()
        stored = registry_service.publish_version(
            manifest=_to_manifest_data(parsed_manifest),
            artifact_bytes=artifact_bytes,
        )
        return _to_detail_response(stored=stored)
    except ValidationError as exc:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_MANIFEST",
            message="Manifest validation failed.",
            details={"errors": exc.errors()},
        )
    except InvalidManifestError as exc:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_MANIFEST",
            message=str(exc),
        )
    except DuplicateSkillVersionError as exc:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_SKILL_VERSION",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )
    except ArtifactStorageFailureError as exc:
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="ARTIFACT_STORAGE_FAILURE",
            message=str(exc),
        )


@router.get("/skills/{skill_id}/{version}", response_model=SkillVersionFetchResponse)
def get_skill_version(
    skill_id: Annotated[str, Path(pattern=SKILL_ID_PATTERN)],
    version: Annotated[str, Path(pattern=SEMVER_PATTERN)],
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionFetchResponse | JSONResponse:
    """Fetch immutable skill version and base64 encoded artifact."""
    return _fetch_skill_version(
        skill_id=skill_id,
        version=version,
        registry_service=registry_service,
    )


def _fetch_skill_version(
    *,
    skill_id: str,
    version: str,
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionFetchResponse | JSONResponse:
    """Fetch and verify immutable version payload."""
    try:
        stored = registry_service.get_version(skill_id=skill_id, version=version)
        return _to_fetch_response(stored=stored)
    except SkillVersionNotFoundError as exc:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SKILL_VERSION_NOT_FOUND",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )
    except IntegrityCheckFailedError as exc:
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTEGRITY_CHECK_FAILED",
            message=str(exc),
            details={"skill_id": exc.skill_id, "version": exc.version},
        )
    except ArtifactStorageFailureError as exc:
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="ARTIFACT_STORAGE_FAILURE",
            message=str(exc),
        )


@router.get("/skills/{skill_id}", response_model=SkillVersionListResponse)
def list_skill_versions(
    skill_id: Annotated[str, Path(pattern=SKILL_ID_PATTERN)],
    registry_service: SkillRegistryServiceDep,
) -> SkillVersionListResponse:
    """List immutable versions for a skill in deterministic order."""
    return _list_skill_versions(skill_id=skill_id, registry_service=registry_service)


def _list_skill_versions(
    *,
    skill_id: str,
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


def _parse_manifest(raw_manifest: str) -> SkillManifest:
    return SkillManifest.model_validate_json(raw_manifest)


def _to_manifest_data(manifest: SkillManifest) -> SkillManifestData:
    return SkillManifestData(
        schema_version=manifest.schema_version,
        skill_id=manifest.skill_id,
        version=manifest.version,
        name=manifest.name,
        description=manifest.description,
        tags=tuple(manifest.tags),
        depends_on=tuple(_to_relationship(item) for item in manifest.depends_on or []),
        extends=tuple(_to_relationship(item) for item in manifest.extends or []),
        conflicts_with=tuple(_to_relationship(item) for item in manifest.conflicts_with or []),
        overlaps_with=tuple(_to_relationship(item) for item in manifest.overlaps_with or []),
    )


def _to_relationship(reference: RelationshipRef) -> SkillRelationshipRef:
    return SkillRelationshipRef(skill_id=reference.skill_id, version=reference.version)


def _to_detail_response(*, stored: SkillVersionDetail) -> SkillVersionDetailResponse:
    return SkillVersionDetailResponse(
        skill_id=stored.skill_id,
        version=stored.version,
        manifest=SkillManifest.model_validate(stored.manifest_json),
        checksum=ChecksumResponse(
            algorithm=stored.checksum.algorithm,
            digest=stored.checksum.digest,
        ),
        artifact_metadata=ArtifactMetadataResponse(
            relative_path=stored.artifact.relative_path,
            size_bytes=stored.artifact.size_bytes,
        ),
        published_at=stored.published_at,
    )


def _to_fetch_response(*, stored: SkillVersionDetail) -> SkillVersionFetchResponse:
    if stored.artifact_bytes is None:
        raise ArtifactStorageFailureError("Artifact bytes were not returned for fetch response.")
    return SkillVersionFetchResponse(
        skill_id=stored.skill_id,
        version=stored.version,
        manifest=SkillManifest.model_validate(stored.manifest_json),
        checksum=ChecksumResponse(
            algorithm=stored.checksum.algorithm,
            digest=stored.checksum.digest,
        ),
        artifact_metadata=ArtifactMetadataResponse(
            relative_path=stored.artifact.relative_path,
            size_bytes=stored.artifact.size_bytes,
        ),
        published_at=stored.published_at,
        artifact_base64=base64.b64encode(stored.artifact_bytes).decode("ascii"),
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))
