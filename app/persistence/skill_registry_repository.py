"""SQLAlchemy adapters for immutable skill catalog persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, Text, bindparam, select, text, tuple_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.ports import (
    ChecksumExpectation,
    ExactSkillCoordinate,
    SearchCandidatesRequest,
    SkillRegistryPersistenceError,
    SkillRegistryPort,
    SkillRelationshipReadPort,
    SkillSearchPort,
    SkillVersionReadPort,
    StoredSkillRelationshipSource,
    StoredSkillSearchCandidate,
    StoredSkillVersion,
    StoredSkillVersionSummary,
)
from app.core.skill_registry import DuplicateSkillVersionError
from app.persistence.models.skill import Skill
from app.persistence.models.skill_relationship_edge import SkillRelationshipEdge
from app.persistence.models.skill_search_document import SkillSearchDocument
from app.persistence.models.skill_version import SkillVersion
from app.persistence.models.skill_version_checksum import SkillVersionChecksum

_RELATIONSHIP_TYPES = ("depends_on", "extends")
_SEARCH_CANDIDATES_SQL = text(
    """
    WITH filtered AS (
        SELECT
            doc.skill_version_fk,
            doc.skill_id,
            doc.version,
            doc.name,
            doc.description,
            doc.tags,
            doc.published_at,
            doc.artifact_size_bytes,
            doc.usage_count,
            CASE
                WHEN :query_text IS NOT NULL AND doc.normalized_skill_id = :query_text THEN TRUE
                ELSE FALSE
            END AS exact_skill_id_match,
            CASE
                WHEN :query_text IS NOT NULL AND doc.normalized_name = :query_text THEN TRUE
                ELSE FALSE
            END AS exact_name_match,
            CASE
                WHEN :query_text IS NOT NULL THEN ts_rank_cd(
                    doc.search_vector,
                    plainto_tsquery('simple'::regconfig, :query_text)
                )
                ELSE 0.0
            END AS lexical_score,
            CASE
                WHEN :required_tag_count > 0 THEN (
                    SELECT COUNT(*)
                    FROM unnest(doc.normalized_tags) AS tag
                    WHERE tag = ANY(:required_tags)
                )
                ELSE 0
            END AS tag_overlap_count
        FROM skill_search_documents AS doc
        WHERE (
            :query_text IS NULL
            OR doc.search_vector @@ plainto_tsquery('simple'::regconfig, :query_text)
            OR doc.normalized_skill_id = :query_text
            OR doc.normalized_name = :query_text
        )
          AND (
            :required_tag_count = 0
            OR doc.normalized_tags @> :required_tags
          )
          AND (
            :published_after IS NULL
            OR doc.published_at >= :published_after
          )
          AND (
            :max_footprint_bytes IS NULL
            OR doc.artifact_size_bytes <= :max_footprint_bytes
          )
    ),
    ranked AS (
        SELECT
            filtered.*,
            ROW_NUMBER() OVER (
                PARTITION BY filtered.skill_id
                ORDER BY
                    filtered.exact_skill_id_match DESC,
                    filtered.exact_name_match DESC,
                    filtered.lexical_score DESC,
                    filtered.tag_overlap_count DESC,
                    filtered.usage_count DESC,
                    filtered.published_at DESC,
                    filtered.artifact_size_bytes ASC,
                    filtered.skill_id ASC,
                    filtered.skill_version_fk DESC
            ) AS skill_rank
        FROM filtered
    )
    SELECT
        skill_version_fk,
        skill_id,
        version,
        name,
        description,
        tags,
        published_at,
        artifact_size_bytes,
        usage_count,
        exact_skill_id_match,
        exact_name_match,
        lexical_score,
        tag_overlap_count
    FROM ranked
    WHERE skill_rank = 1
    ORDER BY
        exact_skill_id_match DESC,
        exact_name_match DESC,
        lexical_score DESC,
        tag_overlap_count DESC,
        usage_count DESC,
        published_at DESC,
        artifact_size_bytes ASC,
        skill_id ASC,
        skill_version_fk DESC
    LIMIT :limit
    """
).bindparams(
    bindparam("query_text", type_=Text()),
    bindparam("required_tags", type_=ARRAY(Text())),
    bindparam("required_tag_count", type_=Integer()),
    bindparam("published_after", type_=DateTime(timezone=True)),
    bindparam("max_footprint_bytes", type_=BigInteger()),
    bindparam("limit", type_=Integer()),
)


class SQLAlchemySkillRegistryRepository(
    SkillRegistryPort,
    SkillVersionReadPort,
    SkillSearchPort,
    SkillRelationshipReadPort,
):
    """SQLAlchemy implementation for immutable skill catalog persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def version_exists(self, *, skill_id: str, version: str) -> bool:
        with self._session_factory() as session:
            statement = (
                select(SkillVersion.id)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .where(Skill.skill_id == skill_id, SkillVersion.version == version)
                .limit(1)
            )
            return session.execute(statement).scalar_one_or_none() is not None

    def create_version(
        self,
        *,
        manifest_json: dict[str, Any],
        artifact_relative_path: str,
        artifact_size_bytes: int,
        checksum: ChecksumExpectation,
    ) -> StoredSkillVersion:
        skill_id = str(manifest_json["skill_id"])
        version = str(manifest_json["version"])

        with self._session_factory() as session:
            try:
                skill = self._get_or_create_skill(session=session, skill_id=skill_id)
                skill_version = SkillVersion(
                    skill_fk=skill.id,
                    version=version,
                    manifest_json=manifest_json,
                    artifact_rel_path=artifact_relative_path,
                    artifact_size_bytes=artifact_size_bytes,
                )
                session.add(skill_version)
                session.flush()
                session.refresh(skill_version, attribute_names=["published_at"])

                session.add_all(
                    _build_relationship_edges(
                        source_skill_version_id=skill_version.id,
                        manifest_json=manifest_json,
                    )
                )
                session.add(
                    _build_search_document(
                        skill_version_id=skill_version.id,
                        manifest_json=manifest_json,
                        artifact_size_bytes=artifact_size_bytes,
                        published_at=skill_version.published_at,
                    )
                )

                checksum_row = SkillVersionChecksum(
                    skill_version_fk=skill_version.id,
                    algorithm=checksum.algorithm,
                    digest=checksum.digest,
                )
                session.add(checksum_row)
                session.commit()

                session.refresh(skill_version)
                session.refresh(checksum_row)
                return _to_stored_skill_version(skill_version=skill_version, checksum=checksum_row)
            except IntegrityError as exc:
                session.rollback()
                if _is_duplicate_skill_version_error(exc):
                    raise DuplicateSkillVersionError(skill_id=skill_id, version=version) from exc
                raise SkillRegistryPersistenceError(
                    "Failed to persist immutable skill version."
                ) from exc
            except SQLAlchemyError as exc:
                session.rollback()
                raise SkillRegistryPersistenceError(
                    "Failed to persist immutable skill version."
                ) from exc

    def get_version(self, *, skill_id: str, version: str) -> StoredSkillVersion | None:
        with self._session_factory() as session:
            statement = (
                select(SkillVersion, SkillVersionChecksum)
                .select_from(SkillVersion)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .join(
                    SkillVersionChecksum,
                    SkillVersionChecksum.skill_version_fk == SkillVersion.id,
                )
                .where(Skill.skill_id == skill_id, SkillVersion.version == version)
            )
            row = session.execute(statement).one_or_none()
            if row is None:
                return None

            skill_version, checksum = row
            return _to_stored_skill_version(skill_version=skill_version, checksum=checksum)

    def get_versions_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillVersion, ...]:
        if not coordinates:
            return ()

        coordinate_pairs = [(item.skill_id, item.version) for item in coordinates]
        with self._session_factory() as session:
            statement = (
                select(SkillVersion, SkillVersionChecksum)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .join(
                    SkillVersionChecksum,
                    SkillVersionChecksum.skill_version_fk == SkillVersion.id,
                )
                .where(tuple_(Skill.skill_id, SkillVersion.version).in_(coordinate_pairs))
            )
            rows = session.execute(statement).all()
            return tuple(
                _to_stored_skill_version(skill_version=skill_version, checksum=checksum)
                for skill_version, checksum in rows
            )

    def get_version_summaries_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillVersionSummary, ...]:
        if not coordinates:
            return ()

        coordinate_pairs = [(item.skill_id, item.version) for item in coordinates]
        with self._session_factory() as session:
            statement = (
                select(SkillVersion, SkillVersionChecksum, Skill.skill_id)
                .select_from(SkillVersion)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .join(
                    SkillVersionChecksum,
                    SkillVersionChecksum.skill_version_fk == SkillVersion.id,
                )
                .where(tuple_(Skill.skill_id, SkillVersion.version).in_(coordinate_pairs))
            )
            rows = session.execute(statement).all()
            return tuple(
                StoredSkillVersionSummary(
                    skill_id=str(skill_id),
                    version=skill_version.version,
                    manifest_json=_ensure_manifest_dict(skill_version.manifest_json),
                    artifact_relative_path=skill_version.artifact_rel_path,
                    artifact_size_bytes=skill_version.artifact_size_bytes,
                    checksum_algorithm=checksum.algorithm,
                    checksum_digest=checksum.digest,
                    published_at=skill_version.published_at,
                )
                for skill_version, checksum, skill_id in rows
            )

    def list_versions(self, *, skill_id: str) -> tuple[StoredSkillVersionSummary, ...]:
        with self._session_factory() as session:
            statement = (
                select(SkillVersion, SkillVersionChecksum)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .join(
                    SkillVersionChecksum,
                    SkillVersionChecksum.skill_version_fk == SkillVersion.id,
                )
                .where(Skill.skill_id == skill_id)
                .order_by(SkillVersion.published_at.desc(), SkillVersion.id.desc())
            )
            rows = session.execute(statement).all()
            return tuple(
                StoredSkillVersionSummary(
                    skill_id=skill_id,
                    version=skill_version.version,
                    manifest_json=_ensure_manifest_dict(skill_version.manifest_json),
                    artifact_relative_path=skill_version.artifact_rel_path,
                    artifact_size_bytes=skill_version.artifact_size_bytes,
                    checksum_algorithm=checksum.algorithm,
                    checksum_digest=checksum.digest,
                    published_at=skill_version.published_at,
                )
                for skill_version, checksum in rows
            )

    def get_relationship_sources_batch(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
    ) -> tuple[StoredSkillRelationshipSource, ...]:
        if not coordinates:
            return ()

        coordinate_pairs = [(item.skill_id, item.version) for item in coordinates]
        with self._session_factory() as session:
            statement = (
                select(
                    Skill.skill_id,
                    SkillVersion.version,
                    SkillVersion.manifest_json,
                    SkillVersion.published_at,
                )
                .select_from(SkillVersion)
                .join(Skill, Skill.id == SkillVersion.skill_fk)
                .where(tuple_(Skill.skill_id, SkillVersion.version).in_(coordinate_pairs))
            )
            rows = session.execute(statement).all()
            return tuple(
                StoredSkillRelationshipSource(
                    skill_id=str(skill_id),
                    version=str(version),
                    manifest_json=_ensure_manifest_dict(manifest_json),
                    published_at=_ensure_datetime(published_at),
                )
                for skill_id, version, manifest_json, published_at in rows
            )

    def search_candidates(
        self,
        *,
        request: SearchCandidatesRequest,
    ) -> tuple[StoredSkillSearchCandidate, ...]:
        published_after = None
        if request.fresh_within_days is not None:
            published_after = datetime.now(UTC) - timedelta(days=request.fresh_within_days)

        with self._session_factory() as session:
            rows = session.execute(
                _SEARCH_CANDIDATES_SQL,
                {
                    "query_text": request.query_text,
                    "required_tags": list(request.required_tags),
                    "required_tag_count": len(request.required_tags),
                    "published_after": published_after,
                    "max_footprint_bytes": request.max_footprint_bytes,
                    "limit": request.limit,
                },
            ).mappings()
            return tuple(
                StoredSkillSearchCandidate(
                    skill_version_fk=int(row["skill_version_fk"]),
                    skill_id=str(row["skill_id"]),
                    version=str(row["version"]),
                    name=str(row["name"]),
                    description=str(row["description"]) if row["description"] is not None else None,
                    tags=tuple(_ensure_string_list(row["tags"])),
                    published_at=_ensure_datetime(row["published_at"]),
                    artifact_size_bytes=int(row["artifact_size_bytes"]),
                    usage_count=int(row["usage_count"]),
                    exact_skill_id_match=bool(row["exact_skill_id_match"]),
                    exact_name_match=bool(row["exact_name_match"]),
                    lexical_score=float(row["lexical_score"]),
                    tag_overlap_count=int(row["tag_overlap_count"]),
                )
                for row in rows
            )

    @staticmethod
    def _get_or_create_skill(*, session: Session, skill_id: str) -> Skill:
        existing = session.execute(
            select(Skill).where(Skill.skill_id == skill_id),
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        created = Skill(skill_id=skill_id)
        session.add(created)
        session.flush()
        return created


def _to_stored_skill_version(
    *,
    skill_version: SkillVersion,
    checksum: SkillVersionChecksum,
) -> StoredSkillVersion:
    return StoredSkillVersion(
        skill_id=str(skill_version.manifest_json["skill_id"]),
        version=skill_version.version,
        manifest_json=_ensure_manifest_dict(skill_version.manifest_json),
        artifact_relative_path=skill_version.artifact_rel_path,
        artifact_size_bytes=skill_version.artifact_size_bytes,
        checksum_algorithm=checksum.algorithm,
        checksum_digest=checksum.digest,
        published_at=_ensure_datetime(skill_version.published_at),
    )


def _build_search_document(
    *,
    skill_version_id: int,
    manifest_json: dict[str, Any],
    artifact_size_bytes: int,
    published_at: datetime | None,
) -> SkillSearchDocument:
    skill_id = str(manifest_json["skill_id"])
    name = str(manifest_json.get("name") or skill_id)
    description = manifest_json.get("description")
    raw_tags = manifest_json.get("tags")
    tags = _ensure_string_list(raw_tags) if isinstance(raw_tags, list) else []

    return SkillSearchDocument(
        skill_version_fk=skill_version_id,
        skill_id=skill_id,
        normalized_skill_id=_normalize_text(skill_id),
        version=str(manifest_json["version"]),
        name=name,
        normalized_name=_normalize_text(name),
        description=str(description) if isinstance(description, str) else None,
        tags=tags,
        normalized_tags=sorted({_normalize_text(tag) for tag in tags if tag.strip()}),
        published_at=_ensure_datetime(published_at),
        artifact_size_bytes=artifact_size_bytes,
        usage_count=0,
    )


def _build_relationship_edges(
    *,
    source_skill_version_id: int,
    manifest_json: dict[str, Any],
) -> tuple[SkillRelationshipEdge, ...]:
    relationships: set[tuple[str, str, str]] = set()
    for edge_type in _RELATIONSHIP_TYPES:
        raw_entries = manifest_json.get(edge_type)
        if not isinstance(raw_entries, list):
            continue
        for item in raw_entries:
            if not isinstance(item, dict):
                continue
            target_skill_id = item.get("skill_id")
            target_version_selector = _extract_target_version_selector(
                edge_type=edge_type,
                item=item,
            )
            if not isinstance(target_skill_id, str) or not isinstance(target_version_selector, str):
                continue
            if not target_skill_id or not target_version_selector:
                continue
            relationships.add((edge_type, target_skill_id, target_version_selector))

    return tuple(
        SkillRelationshipEdge(
            source_skill_version_fk=source_skill_version_id,
            edge_type=edge_type,
            target_skill_id=target_skill_id,
            target_version_selector=target_version_selector,
        )
        for edge_type, target_skill_id, target_version_selector in sorted(relationships)
    )


def _extract_target_version_selector(*, edge_type: str, item: dict[str, Any]) -> str | None:
    raw_version = item.get("version")
    if isinstance(raw_version, str):
        return raw_version

    if edge_type != "depends_on":
        return None

    raw_constraint = item.get("version_constraint")
    if isinstance(raw_constraint, str):
        return raw_constraint

    return None


def _is_duplicate_skill_version_error(error: IntegrityError) -> bool:
    message = str(error.orig).lower()
    return (
        "uq_skill_versions_skill_fk_version" in message
        or "unique constraint" in message
        or "duplicate key value" in message
    )


def _ensure_manifest_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    raise SkillRegistryPersistenceError("Skill manifest payload is not a dictionary.")


def _ensure_string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        raise SkillRegistryPersistenceError("Expected a list of strings.")
    if not all(isinstance(item, str) for item in raw):
        raise SkillRegistryPersistenceError("Expected a list of strings.")
    return [str(item) for item in raw]


def _ensure_datetime(value: datetime | None) -> datetime:
    if value is None:
        raise SkillRegistryPersistenceError("Published timestamp is missing.")
    return value


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip().lower()
