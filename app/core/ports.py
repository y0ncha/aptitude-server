"""Core ports that define boundary contracts for infrastructure adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ExactSkillCoordinate:
    """Exact immutable skill-version selector used by fetch and resolution reads."""

    skill_id: str
    version: str


@dataclass(frozen=True, slots=True)
class ArtifactWriteResult:
    """Details about a newly persisted immutable artifact."""

    relative_path: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class StoredSkillVersion:
    """Persistence projection for a single immutable skill version."""

    skill_id: str
    version: str
    manifest_json: dict[str, Any]
    artifact_relative_path: str
    artifact_size_bytes: int
    checksum_algorithm: str
    checksum_digest: str
    published_at: datetime


@dataclass(frozen=True, slots=True)
class StoredSkillVersionSummary:
    """Persistence projection used by version listing APIs."""

    skill_id: str
    version: str
    manifest_json: dict[str, Any]
    artifact_relative_path: str
    artifact_size_bytes: int
    checksum_algorithm: str
    checksum_digest: str
    published_at: datetime


@dataclass(frozen=True, slots=True)
class StoredSkillRelationshipSource:
    """Relationship source projection backed by immutable stored manifest data."""

    skill_id: str
    version: str
    manifest_json: dict[str, Any]
    published_at: datetime


@dataclass(frozen=True, slots=True)
class SearchCandidatesRequest:
    """Normalized discovery request sent to the persistence search adapter."""

    query_text: str | None
    required_tags: tuple[str, ...]
    fresh_within_days: int | None
    max_footprint_bytes: int | None
    limit: int


@dataclass(frozen=True, slots=True)
class StoredSkillSearchCandidate:
    """Persistence projection for one ranked search candidate."""

    skill_version_fk: int
    skill_id: str
    version: str
    name: str
    description: str | None
    tags: tuple[str, ...]
    published_at: datetime
    artifact_size_bytes: int
    usage_count: int
    exact_skill_id_match: bool
    exact_name_match: bool
    lexical_score: float
    tag_overlap_count: int


@dataclass(frozen=True, slots=True)
class ChecksumExpectation:
    """Checksum data used to persist an immutable version."""

    algorithm: str
    digest: str


class ArtifactStoreError(RuntimeError):
    """Raised when immutable artifact storage fails."""


class ArtifactAlreadyExistsError(ArtifactStoreError):
    """Raised when attempting to create an artifact that already exists."""


class SkillRegistryPersistenceError(RuntimeError):
    """Raised for non-domain-specific persistence failures."""


class SkillRegistryPort(Protocol):
    """Persistence contract for immutable skill version records."""

    def version_exists(self, *, skill_id: str, version: str) -> bool:
        """Return whether a skill version already exists."""

    def create_version(
        self,
        *,
        manifest_json: dict[str, Any],
        artifact_relative_path: str,
        artifact_size_bytes: int,
        checksum: ChecksumExpectation,
    ) -> StoredSkillVersion:
        """Create immutable version, including checksum data."""

    def get_version(self, *, skill_id: str, version: str) -> StoredSkillVersion | None:
        """Return a specific immutable version, if present."""

    def list_versions(self, *, skill_id: str) -> tuple[StoredSkillVersionSummary, ...]:
        """Return deterministic summaries for all versions of a skill."""


class SkillVersionReadPort(Protocol):
    """Read-only persistence contract for exact immutable version metadata."""

    def get_version(self, *, skill_id: str, version: str) -> StoredSkillVersion | None:
        """Return a specific immutable version, if present."""

    def get_versions_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillVersion, ...]:
        """Return exact immutable versions for the requested coordinates."""

    def get_version_summaries_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillVersionSummary, ...]:
        """Return summaries for exact immutable version coordinates."""


class SkillSearchPort(Protocol):
    """Persistence contract for advisory search candidate retrieval."""

    def search_candidates(
        self,
        *,
        request: SearchCandidatesRequest,
    ) -> tuple[StoredSkillSearchCandidate, ...]:
        """Return ranked skill candidates for the provided discovery request."""


class SkillRelationshipReadPort(Protocol):
    """Read-only persistence contract for direct relationship source lookup."""

    def get_relationship_sources_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillRelationshipSource, ...]:
        """Return stored relationship sources for the requested coordinates."""


class ArtifactReadPort(Protocol):
    """Read-only artifact access contract used by exact fetch services."""

    def read_artifact(self, *, relative_path: str) -> bytes:
        """Read immutable artifact bytes by relative path."""


class ArtifactStorePort(ArtifactReadPort, Protocol):
    """Storage contract for immutable artifact file handling."""

    def store_immutable_artifact(
        self,
        *,
        skill_id: str,
        version: str,
        artifact_bytes: bytes,
        manifest_json: dict[str, Any],
    ) -> ArtifactWriteResult:
        """Persist artifact and manifest snapshot under immutable paths."""


class AuditPort(Protocol):
    """Audit recording contract used by core services."""

    def record_event(self, *, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Persist a domain audit event."""


class DatabaseReadinessPort(Protocol):
    """Contract for probing database readiness from the core layer."""

    def ping(self) -> tuple[bool, str | None]:
        """Return (is_ready, detail)."""
