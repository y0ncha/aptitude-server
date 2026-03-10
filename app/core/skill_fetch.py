"""Core exact fetch service for immutable version metadata and artifact reads."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.ports import ArtifactReadPort, ExactSkillCoordinate, SkillVersionReadPort
from app.core.skill_registry import (
    SHA256_ALGORITHM,
    ArtifactStorageFailureError,
    IntegrityCheckFailedError,
    SkillArtifactMetadata,
    SkillChecksum,
    SkillVersionDetail,
    SkillVersionNotFoundError,
    SkillVersionSummary,
)


@dataclass(frozen=True, slots=True)
class SkillFetchBatchItem:
    """Ordered exact fetch result for one requested coordinate."""

    coordinate: ExactSkillCoordinate
    version: SkillVersionSummary | None


class SkillFetchService:
    """Read-only service for exact immutable metadata and artifact access."""

    def __init__(
        self,
        *,
        version_reader: SkillVersionReadPort,
        artifact_reader: ArtifactReadPort,
    ) -> None:
        self._version_reader = version_reader
        self._artifact_reader = artifact_reader

    def get_version_metadata(self, *, skill_id: str, version: str) -> SkillVersionSummary:
        """Return one immutable version metadata projection without loading artifact bytes."""
        stored = self._version_reader.get_version(skill_id=skill_id, version=version)
        if stored is None:
            raise SkillVersionNotFoundError(skill_id=skill_id, version=version)
        return _to_summary(
            skill_id=stored.skill_id,
            version=stored.version,
            manifest_json=stored.manifest_json,
            checksum_algorithm=stored.checksum_algorithm,
            checksum_digest=stored.checksum_digest,
            artifact_relative_path=stored.artifact_relative_path,
            artifact_size_bytes=stored.artifact_size_bytes,
            published_at=stored.published_at,
        )

    def get_version_metadata_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[SkillFetchBatchItem, ...]:
        """Return ordered exact metadata results for the requested coordinates."""
        stored_versions = self._version_reader.get_versions_batch(coordinates=coordinates)
        by_key = {(item.skill_id, item.version): item for item in stored_versions}
        return tuple(
            SkillFetchBatchItem(
                coordinate=coordinate,
                version=(
                    None
                    if (stored := by_key.get((coordinate.skill_id, coordinate.version))) is None
                    else _to_summary(
                        skill_id=stored.skill_id,
                        version=stored.version,
                        manifest_json=stored.manifest_json,
                        checksum_algorithm=stored.checksum_algorithm,
                        checksum_digest=stored.checksum_digest,
                        artifact_relative_path=stored.artifact_relative_path,
                        artifact_size_bytes=stored.artifact_size_bytes,
                        published_at=stored.published_at,
                    )
                ),
            )
            for coordinate in coordinates
        )

    def get_artifact(self, *, skill_id: str, version: str) -> SkillVersionDetail:
        """Return one immutable version and verified artifact bytes."""
        stored = self._version_reader.get_version(skill_id=skill_id, version=version)
        if stored is None:
            raise SkillVersionNotFoundError(skill_id=skill_id, version=version)

        try:
            artifact_bytes = self._artifact_reader.read_artifact(
                relative_path=stored.artifact_relative_path
            )
        except Exception as exc:  # pragma: no cover - error type normalized by adapter contract
            raise ArtifactStorageFailureError("Artifact storage read failed.") from exc

        computed_checksum = hashlib.sha256(artifact_bytes).hexdigest()
        if computed_checksum != stored.checksum_digest:
            raise IntegrityCheckFailedError(skill_id=skill_id, version=version)

        return SkillVersionDetail(
            skill_id=stored.skill_id,
            version=stored.version,
            manifest_json=stored.manifest_json,
            checksum=SkillChecksum(
                algorithm=stored.checksum_algorithm,
                digest=stored.checksum_digest,
            ),
            artifact=SkillArtifactMetadata(
                relative_path=stored.artifact_relative_path,
                size_bytes=stored.artifact_size_bytes,
            ),
            published_at=stored.published_at,
            artifact_bytes=artifact_bytes,
        )


def _to_summary(
    *,
    skill_id: str,
    version: str,
    manifest_json: dict[str, object],
    checksum_algorithm: str,
    checksum_digest: str,
    artifact_relative_path: str,
    artifact_size_bytes: int,
    published_at,
) -> SkillVersionSummary:
    return SkillVersionSummary(
        skill_id=skill_id,
        version=version,
        manifest_json=manifest_json,
        checksum=SkillChecksum(
            algorithm=checksum_algorithm or SHA256_ALGORITHM,
            digest=checksum_digest,
        ),
        artifact=SkillArtifactMetadata(
            relative_path=artifact_relative_path,
            size_bytes=artifact_size_bytes,
        ),
        published_at=published_at,
    )

