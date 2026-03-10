"""Core direct-relationship query service for immutable skill versions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.ports import ExactSkillCoordinate, SkillRelationshipReadPort, SkillVersionReadPort
from app.core.skill_registry import SkillVersionSummary

SUPPORTED_RELATIONSHIP_EDGE_TYPES = ("depends_on", "extends")


@dataclass(frozen=True, slots=True)
class SkillRelationshipSelector:
    """Authored relationship selector preserved from the published manifest."""

    skill_id: str
    version: str | None = None
    version_constraint: str | None = None
    optional: bool | None = None
    markers: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class SkillRelationship:
    """Direct authored relationship edge returned by the core read service."""

    edge_type: str
    selector: SkillRelationshipSelector
    target_version: SkillVersionSummary | None


@dataclass(frozen=True, slots=True)
class SkillRelationshipBatchItem:
    """Ordered direct-relationship lookup result for one source coordinate."""

    coordinate: ExactSkillCoordinate
    relationships: tuple[SkillRelationship, ...] | None


class SkillRelationshipService:
    """Read-only direct relationship service with no solving behavior."""

    def __init__(
        self,
        *,
        relationship_reader: SkillRelationshipReadPort,
        version_reader: SkillVersionReadPort,
    ) -> None:
        self._relationship_reader = relationship_reader
        self._version_reader = version_reader

    def get_direct_relationships(
        self,
        *,
        coordinates: tuple[ExactSkillCoordinate, ...],
        edge_types: tuple[str, ...],
    ) -> tuple[SkillRelationshipBatchItem, ...]:
        """Return authored direct relationships for the requested sources."""
        normalized_edge_types = _normalize_edge_types(edge_types)
        stored_sources = self._relationship_reader.get_relationship_sources_batch(
            coordinates=coordinates
        )
        source_by_key = {(item.skill_id, item.version): item for item in stored_sources}

        exact_target_coordinates: list[ExactSkillCoordinate] = []
        authored_relationships: dict[tuple[str, str], tuple[SkillRelationship, ...]] = {}
        for coordinate in coordinates:
            stored = source_by_key.get((coordinate.skill_id, coordinate.version))
            if stored is None:
                continue

            relationships = tuple(
                relationship
                for edge_type in normalized_edge_types
                for relationship in _relationships_from_manifest_edge_type(
                    edge_type=edge_type,
                    manifest_json=stored.manifest_json,
                    exact_target_coordinates=exact_target_coordinates,
                )
            )
            authored_relationships[(coordinate.skill_id, coordinate.version)] = relationships

        exact_target_summaries = self._version_reader.get_version_summaries_batch(
            coordinates=tuple(exact_target_coordinates)
        )
        target_by_key = {(item.skill_id, item.version): item for item in exact_target_summaries}

        return tuple(
            SkillRelationshipBatchItem(
                coordinate=coordinate,
                relationships=(
                    None
                    if (coordinate.skill_id, coordinate.version) not in authored_relationships
                    else tuple(
                        SkillRelationship(
                            edge_type=item.edge_type,
                            selector=item.selector,
                            target_version=(
                                None
                                if item.selector.version is None
                                else target_by_key.get(
                                    (item.selector.skill_id, item.selector.version)
                                )
                            ),
                        )
                        for item in authored_relationships[
                            (coordinate.skill_id, coordinate.version)
                        ]
                    )
                ),
            )
            for coordinate in coordinates
        )


def _normalize_edge_types(edge_types: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for edge_type in edge_types:
        if edge_type not in SUPPORTED_RELATIONSHIP_EDGE_TYPES:
            continue
        if edge_type in seen:
            continue
        seen.add(edge_type)
        normalized.append(edge_type)
    return tuple(normalized or SUPPORTED_RELATIONSHIP_EDGE_TYPES)


def _relationships_from_manifest_edge_type(
    *,
    edge_type: str,
    manifest_json: dict[str, Any],
    exact_target_coordinates: list[ExactSkillCoordinate],
) -> tuple[SkillRelationship, ...]:
    raw_entries = manifest_json.get(edge_type)
    if not isinstance(raw_entries, list):
        return ()

    relationships: list[SkillRelationship] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        skill_id = item.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id:
            continue

        selector = SkillRelationshipSelector(
            skill_id=skill_id,
            version=item.get("version") if isinstance(item.get("version"), str) else None,
            version_constraint=(
                item.get("version_constraint")
                if isinstance(item.get("version_constraint"), str)
                else None
            ),
            optional=item.get("optional") if isinstance(item.get("optional"), bool) else None,
            markers=(
                tuple(marker for marker in item["markers"] if isinstance(marker, str))
                if isinstance(item.get("markers"), list)
                else None
            ),
        )
        if selector.version is not None:
            exact_target_coordinates.append(
                ExactSkillCoordinate(skill_id=selector.skill_id, version=selector.version)
            )

        relationships.append(
            SkillRelationship(
                edge_type=edge_type,
                selector=selector,
                target_version=None,
            )
        )

    return tuple(relationships)

