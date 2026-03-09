# Plan 05 — Metadata Search and Ranking

## Goal
Provide high-performance candidate retrieval and advisory ranking over metadata and descriptions in the repository service.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Search and indexing: PostgreSQL native full-text and index strategy from milestone 1

## Scope
- Add metadata model (`freshness`, `footprint`, `usage_count`, provenance fields).
- Build indexing and query path for metadata-driven filtering and text search over names, descriptions, and tags.
- Add search endpoint with deterministic candidate ordering.
- Return compact search cards and ranking explanation fields.
- Keep ranking advisory; resolver remains authoritative for reranking, final selection, dependency solving, and lock output.
- Explicitly exclude prompt parsing, personalized ranking, environment-aware selection, and server-side solve behavior.

## Architecture Impact
- Expands metadata and indexing capabilities without violating service boundaries.
- Improves discovery UX while preserving immutable artifact guarantees.
- Pushes indexed retrieval onto the server while keeping agent reasoning on the client/resolver.

## Deliverables
- Endpoint: `GET /v1/skills/search`.
- Metadata tables and PostgreSQL indexes (including full-text search support).
- Ranking rule chain with deterministic fallback.
- Search response fields for ranking rationale.
- Compact candidate result contract tuned for resolver consumption.
- Learning note on candidate retrieval vs final choice and on derived data vs source-of-truth separation.

## Acceptance Criteria
- Search results are relevant to filters and query text.
- Ranking is stable for equal-score candidates.
- Search results remain compact enough for resolver candidate generation without requiring full-manifest over-fetch.
- Metadata updates never mutate skill artifacts.
- Deprecated/archived visibility obeys lifecycle policy defaults.
- Search contract clearly remains advisory and non-authoritative for final resolver choice.

## Test Plan
- Integration tests for filter combinations.
- Deterministic sort tests under tie conditions.
- PostgreSQL full-text tests for name, description, and tag matching.
- Regression tests for ranking rationale fields.
- Contract tests for compact candidate payload shape.
