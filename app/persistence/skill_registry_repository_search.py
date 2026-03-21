"""Search-side SQLAlchemy mixin for advisory discovery candidates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from app.core.governance import LifecycleStatus, TrustTier
from app.core.ports import SearchCandidatesRequest, StoredSkillSearchCandidate
from app.persistence.skill_registry_repository_base import SkillRegistryRepositoryBase
from app.persistence.skill_registry_repository_support import (
    SEARCH_CANDIDATES_SQL,
    build_contains_pattern,
    ensure_datetime,
    ensure_string_list,
)


class SkillRegistrySearchMixin(SkillRegistryRepositoryBase):
    """Search-side methods for advisory candidate retrieval."""

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
                SEARCH_CANDIDATES_SQL,
                {
                    "query_text": request.query_text,
                    "query_contains_pattern": build_contains_pattern(request.query_text),
                    "required_tags": list(request.required_tags),
                    "required_tag_count": len(request.required_tags),
                    "published_after": published_after,
                    "max_content_size_bytes": request.max_content_size_bytes,
                    "lifecycle_statuses": list(request.lifecycle_statuses),
                    "trust_tiers": list(request.trust_tiers),
                    "limit": request.limit,
                },
            ).mappings()
            return tuple(
                StoredSkillSearchCandidate(
                    slug=str(row["slug"]),
                    version=str(row["version"]),
                    name=str(row["name"]),
                    description=str(row["description"]) if row["description"] is not None else None,
                    tags=tuple(ensure_string_list(row["tags"])),
                    lifecycle_status=cast(LifecycleStatus, str(row["lifecycle_status"])),
                    trust_tier=cast(TrustTier, str(row["trust_tier"])),
                    published_at=ensure_datetime(row["published_at"]),
                    content_size_bytes=int(row["content_size_bytes"]),
                    usage_count=int(row["usage_count"]),
                    exact_slug_match=bool(row["exact_slug_match"]),
                    exact_name_match=bool(row["exact_name_match"]),
                    lexical_score=float(row["lexical_score"]),
                    tag_overlap_count=int(row["tag_overlap_count"]),
                )
                for row in rows
            )
