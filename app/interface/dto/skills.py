"""Skill registry DTOs and validation constants."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Core semantic-version regex used both in request validation and path params.
# It accepts MAJOR.MINOR.PATCH plus optional prerelease/build metadata.
SEMVER_CORE = (
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)
SEMVER_PATTERN = rf"^{SEMVER_CORE}$"

# Public skill identifiers are intentionally conservative and stable:
# - must start with an alphanumeric character
# - may then include letters, numbers, ".", "_", or "-"
# - capped at 128 characters
SKILL_ID_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,127})$"

# Dependency constraints allow one or more comma-separated semver comparators,
# for example: ">=1.0.0,<2.0.0".
VERSION_CONSTRAINT_PATTERN = re.compile(
    rf"^\s*(?:==|=|!=|>=|<=|>|<)\s*{SEMVER_CORE}\s*"
    rf"(?:,\s*(?:==|=|!=|>=|<=|>|<)\s*{SEMVER_CORE}\s*)*$"
)

# Execution markers are preserved as authored, but constrained to a small token
# grammar so they remain safe and deterministic to store and compare.
MARKER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
MAX_BATCH_ITEMS = 100
RelationshipEdgeType = Literal["depends_on", "extends"]
BatchItemStatus = Literal["found", "not_found"]


class RelationshipRef(BaseModel):
    """Typed manifest reference to another immutable skill version."""

    skill_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=SKILL_ID_PATTERN,
        description="Stable identifier of the related skill.",
    )
    version: str = Field(
        pattern=SEMVER_PATTERN,
        description="Exact semantic version of the related immutable skill.",
    )

    model_config = ConfigDict(extra="forbid")


class DependencyDeclaration(BaseModel):
    """Direct dependency contract authored for a specific immutable version."""

    skill_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=SKILL_ID_PATTERN,
        description="Stable identifier of the dependency skill.",
    )
    version: str | None = Field(
        default=None,
        pattern=SEMVER_PATTERN,
        description=(
            "Exact immutable dependency version. Mutually exclusive with `version_constraint`."
        ),
    )
    version_constraint: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description=(
            "Comma-separated semver comparators, for example `>=1.0.0,<2.0.0`. "
            "Mutually exclusive with `version`."
        ),
    )
    optional: bool | None = Field(
        default=None,
        description="Whether consumers may omit this dependency at runtime.",
    )
    markers: list[str] | None = Field(
        default=None,
        description="Execution markers preserved exactly as authored in the manifest.",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("markers")
    @classmethod
    def validate_markers(cls, value: list[str] | None) -> list[str] | None:
        """Validate authored marker tokens."""
        if value is None:
            return None

        for marker in value:
            if MARKER_PATTERN.fullmatch(marker) is None:
                raise ValueError(
                    "Dependency declaration markers must be non-empty tokens "
                    "containing only letters, numbers, '.', '_', ':', or '-'."
                )

        return value

    @model_validator(mode="after")
    def validate_version_selector(self) -> DependencyDeclaration:
        """Ensure the dependency uses exactly one version-selection strategy."""
        if (self.version is None) == (self.version_constraint is None):
            raise ValueError(
                "Dependency declaration must include exactly one of `version` "
                "or `version_constraint`."
            )

        if self.version_constraint is not None:
            if VERSION_CONSTRAINT_PATTERN.fullmatch(self.version_constraint) is None:
                raise ValueError(
                    "Dependency declaration `version_constraint` must be a "
                    "comma-separated list of semver comparators."
                )

        return self


class SkillManifest(BaseModel):
    """Validated immutable skill manifest contract."""

    schema_version: str = Field(
        default="1.0",
        min_length=1,
        max_length=20,
        description="Manifest schema version understood by this API.",
    )
    skill_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=SKILL_ID_PATTERN,
        description="Stable catalog identifier for the skill.",
    )
    version: str = Field(
        pattern=SEMVER_PATTERN,
        description="Immutable semantic version being published or fetched.",
    )
    name: str = Field(
        min_length=1,
        max_length=200,
        description="Human-readable skill name.",
    )
    description: str | None = Field(
        default=None,
        description="Optional human-readable summary of the skill.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags used for categorization and discovery.",
    )
    depends_on: list[DependencyDeclaration] | None = Field(
        default=None,
        description="Direct dependency declarations authored for this immutable version.",
    )
    extends: list[RelationshipRef] | None = Field(
        default=None,
        description="Other immutable skill versions this version extends.",
    )
    conflicts_with: list[RelationshipRef] | None = Field(
        default=None,
        description="Immutable skill versions known to conflict with this version.",
    )
    overlaps_with: list[RelationshipRef] | None = Field(
        default=None,
        description="Immutable skill versions with overlapping behavior or scope.",
    )

    model_config = ConfigDict(extra="forbid")


class ChecksumResponse(BaseModel):
    """Checksum metadata attached to a stored artifact."""

    algorithm: str = Field(description="Checksum algorithm used for the artifact.")
    digest: str = Field(description="Hex digest of the stored artifact.")


class ArtifactMetadataResponse(BaseModel):
    """Immutable metadata describing where and how large the artifact is."""

    relative_path: str = Field(
        description="Artifact path relative to the configured artifact root."
    )
    size_bytes: int = Field(description="Stored artifact size in bytes.")


class SkillVersionDetailResponse(BaseModel):
    """Metadata returned after a successful publish or fetch."""

    skill_id: str = Field(description="Stable identifier of the skill.")
    version: str = Field(description="Immutable semantic version of the skill.")
    manifest: SkillManifest = Field(description="Validated manifest as stored by the service.")
    checksum: ChecksumResponse = Field(description="Checksum metadata for integrity checks.")
    artifact_metadata: ArtifactMetadataResponse = Field(
        description="Location and size metadata for the immutable artifact."
    )
    published_at: datetime = Field(description="UTC timestamp when the version was published.")


class SkillVersionFetchResponse(SkillVersionDetailResponse):
    """Fetch response that includes the binary artifact encoded for JSON transport."""

    artifact_base64: str = Field(
        description="Artifact bytes encoded as a base64 ASCII string.",
    )


class SkillVersionSummaryResponse(BaseModel):
    """Summary view for one immutable skill version in a list response."""

    skill_id: str = Field(description="Stable identifier of the skill.")
    version: str = Field(description="Immutable semantic version of the skill.")
    manifest: SkillManifest = Field(description="Validated manifest for the listed version.")
    checksum: ChecksumResponse = Field(description="Checksum metadata for the artifact.")
    artifact_metadata: ArtifactMetadataResponse = Field(
        description="Location and size metadata for the immutable artifact."
    )
    published_at: datetime = Field(description="UTC timestamp when the version was published.")


class SkillVersionListResponse(BaseModel):
    """List of all known immutable versions for a skill."""

    skill_id: str = Field(description="Stable identifier of the skill.")
    versions: list[SkillVersionSummaryResponse] = Field(
        description="Published versions in deterministic reverse chronological order.",
    )


class ExactSkillCoordinateRequest(BaseModel):
    """Exact immutable skill-version coordinate used by fetch and resolution reads."""

    skill_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=SKILL_ID_PATTERN,
        description="Stable identifier of the requested skill.",
    )
    version: str = Field(
        pattern=SEMVER_PATTERN,
        description="Exact immutable semantic version of the requested skill.",
    )

    model_config = ConfigDict(extra="forbid")


class ArtifactRefResponse(BaseModel):
    """Backend-agnostic artifact reference returned by the new fetch APIs."""

    checksum_algorithm: str = Field(description="Checksum algorithm for the immutable artifact.")
    checksum_digest: str = Field(description="Checksum digest for the immutable artifact.")
    size_bytes: int = Field(description="Artifact size in bytes.")
    download_path: str = Field(description="API path clients should call to stream the artifact.")


class ExactSkillVersionResponse(BaseModel):
    """Exact immutable version metadata returned by the new fetch APIs."""

    skill_id: str = Field(description="Stable identifier of the skill.")
    version: str = Field(description="Immutable semantic version of the skill.")
    manifest: SkillManifest = Field(description="Validated manifest as stored by the service.")
    checksum: ChecksumResponse = Field(description="Checksum metadata for integrity checks.")
    artifact_ref: ArtifactRefResponse = Field(
        description="Backend-agnostic reference used to stream the immutable artifact.",
    )
    published_at: datetime = Field(description="UTC timestamp when the version was published.")


class SkillFetchBatchRequest(BaseModel):
    """Ordered batch request for exact immutable version metadata reads."""

    coordinates: list[ExactSkillCoordinateRequest] = Field(
        min_length=1,
        max_length=MAX_BATCH_ITEMS,
        description="Ordered immutable coordinates to read exactly.",
    )

    model_config = ConfigDict(extra="forbid")


class SkillFetchBatchItemResponse(BaseModel):
    """One ordered exact metadata batch result."""

    status: BatchItemStatus = Field(description="Whether the requested coordinate was found.")
    coordinate: ExactSkillCoordinateRequest = Field(
        description="Exact immutable coordinate as requested by the client."
    )
    version: ExactSkillVersionResponse | None = Field(
        default=None,
        description="Returned immutable version metadata when the coordinate exists.",
    )


class SkillFetchBatchResponse(BaseModel):
    """Ordered batch response for exact immutable metadata reads."""

    results: list[SkillFetchBatchItemResponse] = Field(
        description="Ordered per-coordinate fetch results preserving request order.",
    )


class RelationshipSelectorResponse(BaseModel):
    """Authored relationship selector preserved from the immutable manifest."""

    skill_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=SKILL_ID_PATTERN,
        description="Stable identifier of the related skill.",
    )
    version: str | None = Field(
        default=None,
        pattern=SEMVER_PATTERN,
        description="Exact related version when the relationship targets one immutable version.",
    )
    version_constraint: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Authored dependency constraint when the relationship is version-ranged.",
    )
    optional: bool | None = Field(
        default=None,
        description="Optional dependency marker preserved as authored.",
    )
    markers: list[str] | None = Field(
        default=None,
        description="Execution markers preserved exactly as authored.",
    )

    model_config = ConfigDict(extra="forbid")


class RelatedSkillVersionSummaryResponse(BaseModel):
    """Compact exact target summary for direct relationships with exact selectors."""

    skill_id: str = Field(description="Stable identifier of the related skill.")
    version: str = Field(description="Exact immutable semantic version of the related skill.")
    name: str = Field(description="Human-readable skill name.")
    description: str | None = Field(description="Optional human-readable summary.")
    tags: list[str] = Field(description="Searchable tags attached to the related version.")
    published_at: datetime = Field(
        description="UTC timestamp when the related version was published."
    )


class SkillRelationshipEdgeResponse(BaseModel):
    """One direct authored relationship edge from an immutable source version."""

    edge_type: RelationshipEdgeType = Field(
        description="Relationship family preserved from the manifest."
    )
    selector: RelationshipSelectorResponse = Field(
        description="Authored selector preserved exactly from the immutable manifest."
    )
    target_version: RelatedSkillVersionSummaryResponse | None = Field(
        default=None,
        description=(
            "Optional exact target version summary when the selector points to one exact version."
        ),
    )


class SkillRelationshipBatchRequest(BaseModel):
    """Ordered direct relationship query over immutable source versions."""

    coordinates: list[ExactSkillCoordinateRequest] = Field(
        min_length=1,
        max_length=MAX_BATCH_ITEMS,
        description="Ordered immutable source coordinates to inspect.",
    )
    edge_types: list[RelationshipEdgeType] = Field(
        default_factory=lambda: ["depends_on", "extends"],
        description="Relationship families to include. Defaults to `depends_on` and `extends`.",
    )

    model_config = ConfigDict(extra="forbid")


class SkillRelationshipBatchItemResponse(BaseModel):
    """One ordered direct relationship lookup result."""

    status: BatchItemStatus = Field(
        description="Whether the requested source coordinate was found."
    )
    coordinate: ExactSkillCoordinateRequest = Field(
        description="Exact immutable source coordinate as requested by the client."
    )
    relationships: list[SkillRelationshipEdgeResponse] | None = Field(
        default=None,
        description="Direct authored relationships for the source version when it exists.",
    )


class SkillRelationshipBatchResponse(BaseModel):
    """Ordered batch response for direct immutable relationship reads."""

    results: list[SkillRelationshipBatchItemResponse] = Field(
        description="Ordered per-source relationship results preserving request order.",
    )


class SkillSearchRequest(BaseModel):
    """Validated query shape for advisory search requests."""

    q: str | None = Field(
        default=None,
        description=(
            "Optional full-text query over skill identifiers, names, tags, and descriptions."
        ),
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Repeated tag filters. Every provided tag must be present on a result.",
    )
    language: str | None = Field(
        default=None,
        description="Convenience alias for filtering by a language tag.",
    )
    fresh_within_days: int | None = Field(
        default=None,
        ge=0,
        description="Optional upper bound on skill freshness in whole days since publication.",
    )
    max_footprint_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Optional maximum artifact size in bytes.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of compact candidates to return.",
    )

    @field_validator("q", "language")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Trim empty strings down to null so selector validation is stable."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        """Drop empty tag strings while preserving authored order."""
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_has_selector(self) -> SkillSearchRequest:
        """Require at least one discovery selector for server-side search."""
        if (
            self.q is None
            and not self.tags
            and self.language is None
            and self.fresh_within_days is None
            and self.max_footprint_bytes is None
        ):
            raise ValueError("At least one search selector must be provided.")
        return self


class SkillSearchResultResponse(BaseModel):
    """Compact advisory candidate returned by the search API."""

    skill_id: str = Field(description="Stable identifier of the matched skill.")
    version: str = Field(description="Best matching immutable version for this skill.")
    name: str = Field(description="Human-readable skill name.")
    description: str | None = Field(description="Optional short skill description.")
    tags: list[str] = Field(description="Searchable tags attached to the matched version.")
    published_at: datetime = Field(description="UTC timestamp when the version was published.")
    freshness_days: int = Field(description="Whole days since the version was published.")
    footprint_bytes: int = Field(
        description="Artifact size used for compact filtering and ranking."
    )
    usage_count: int = Field(description="Derived usage metric reserved for future ranking inputs.")
    matched_fields: list[str] = Field(
        description="Fields that contributed to the candidate match explanation.",
    )
    matched_tags: list[str] = Field(
        description="Normalized tag filters satisfied by this result.",
    )
    reasons: list[str] = Field(
        description="Stable advisory ranking hints describing why the result matched.",
    )


class SkillSearchResponse(BaseModel):
    """Compact advisory search response."""

    results: list[SkillSearchResultResponse] = Field(
        description="One compact candidate per skill identifier in deterministic order.",
    )
