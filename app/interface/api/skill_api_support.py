"""Shared adapter helpers for skill-related HTTP routers."""

from __future__ import annotations

import base64
from typing import Any

from pydantic import ValidationError

from app.core.skill_registry import (
    ArtifactStorageFailureError,
    SkillDependencyRef,
    SkillManifestData,
    SkillRelationshipRef,
    SkillVersionDetail,
    SkillVersionSummary,
)
from app.core.skill_search import SkillSearchResult
from app.interface.api.errors import serialize_validation_errors
from app.interface.dto.skills import (
    ArtifactMetadataResponse,
    ArtifactRefResponse,
    ChecksumResponse,
    DependencyDeclaration,
    ExactSkillVersionResponse,
    RelatedSkillVersionSummaryResponse,
    RelationshipRef,
    RelationshipSelectorResponse,
    SkillManifest,
    SkillSearchResultResponse,
    SkillVersionDetailResponse,
    SkillVersionFetchResponse,
)


def parse_manifest(raw_manifest: str) -> SkillManifest:
    """Parse multipart manifest JSON into the public API model."""
    return SkillManifest.model_validate_json(raw_manifest)


def validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    """Return JSON-safe Pydantic validation details for the public error envelope."""
    return serialize_validation_errors(exc)


def to_manifest_data(manifest: SkillManifest) -> SkillManifestData:
    """Translate validated API models into immutable core manifest data."""
    return SkillManifestData(
        schema_version=manifest.schema_version,
        skill_id=manifest.skill_id,
        version=manifest.version,
        name=manifest.name,
        description=manifest.description,
        tags=tuple(manifest.tags),
        depends_on=tuple(to_dependency(item) for item in manifest.depends_on or []),
        extends=tuple(to_relationship(item) for item in manifest.extends or []),
        conflicts_with=tuple(to_relationship(item) for item in manifest.conflicts_with or []),
        overlaps_with=tuple(to_relationship(item) for item in manifest.overlaps_with or []),
        raw_manifest_json=manifest.model_dump(exclude_unset=True, mode="json"),
    )


def to_relationship(reference: RelationshipRef) -> SkillRelationshipRef:
    """Project an API relationship reference into the core domain shape."""
    return SkillRelationshipRef(skill_id=reference.skill_id, version=reference.version)


def to_dependency(reference: DependencyDeclaration) -> SkillDependencyRef:
    """Project an API dependency declaration into the core domain shape."""
    return SkillDependencyRef(
        skill_id=reference.skill_id,
        version=reference.version,
        version_constraint=reference.version_constraint,
        optional=reference.optional,
        markers=tuple(reference.markers) if reference.markers is not None else None,
    )


def to_detail_response(*, stored: SkillVersionDetail) -> SkillVersionDetailResponse:
    """Convert a core detail projection into the publish response schema."""
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


def to_legacy_fetch_response(*, stored: SkillVersionDetail) -> SkillVersionFetchResponse:
    """Convert a core detail projection into the legacy combined fetch schema."""
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


def to_exact_version_response(
    *,
    stored: SkillVersionSummary,
    download_path: str,
) -> ExactSkillVersionResponse:
    """Convert exact immutable version metadata into the new fetch response schema."""
    return ExactSkillVersionResponse(
        skill_id=stored.skill_id,
        version=stored.version,
        manifest=SkillManifest.model_validate(stored.manifest_json),
        checksum=ChecksumResponse(
            algorithm=stored.checksum.algorithm,
            digest=stored.checksum.digest,
        ),
        artifact_ref=ArtifactRefResponse(
            checksum_algorithm=stored.checksum.algorithm,
            checksum_digest=stored.checksum.digest,
            size_bytes=stored.artifact.size_bytes,
            download_path=download_path,
        ),
        published_at=stored.published_at,
    )


def to_related_skill_version_summary(
    *,
    stored: SkillVersionSummary,
) -> RelatedSkillVersionSummaryResponse:
    """Convert exact immutable version metadata into a compact relationship summary."""
    manifest = SkillManifest.model_validate(stored.manifest_json)
    return RelatedSkillVersionSummaryResponse(
        skill_id=stored.skill_id,
        version=stored.version,
        name=manifest.name,
        description=manifest.description,
        tags=list(manifest.tags),
        published_at=stored.published_at,
    )


def to_search_result_response(item: SkillSearchResult) -> SkillSearchResultResponse:
    """Convert a core search result into the compact HTTP search card."""
    return SkillSearchResultResponse(
        skill_id=item.skill_id,
        version=item.version,
        name=item.name,
        description=item.description,
        tags=list(item.tags),
        published_at=item.published_at,
        freshness_days=item.freshness_days,
        footprint_bytes=item.footprint_bytes,
        usage_count=item.usage_count,
        matched_fields=list(item.matched_fields),
        matched_tags=list(item.matched_tags),
        reasons=list(item.reasons),
    )


def artifact_download_path(*, skill_id: str, version: str) -> str:
    """Return the stable API path clients should call to stream the artifact."""
    return f"/fetch/skills/{skill_id}/{version}/artifact"


def legacy_artifact_download_path(*, skill_id: str, version: str) -> str:
    """Return the legacy exact fetch path for compatibility documentation."""
    return f"/skills/{skill_id}/{version}"


def relationship_selector_response(
    *,
    skill_id: str,
    version: str | None,
    version_constraint: str | None,
    optional: bool | None,
    markers: tuple[str, ...] | None,
) -> RelationshipSelectorResponse:
    """Build the public relationship selector response."""
    payload: dict[str, Any] = {"skill_id": skill_id}
    if version is not None:
        payload["version"] = version
    if version_constraint is not None:
        payload["version_constraint"] = version_constraint
    if optional is not None:
        payload["optional"] = optional
    if markers is not None:
        payload["markers"] = list(markers)
    return RelationshipSelectorResponse(**payload)
