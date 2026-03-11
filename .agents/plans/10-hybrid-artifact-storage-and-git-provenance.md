# Plan 10 - PostgreSQL Artifact Storage and Git Provenance

Legacy filename retained under the append-only roadmap rule. This plan now reflects the PostgreSQL split-table storage decision.

## Goal
Keep PostgreSQL authoritative for registry metadata, digest mappings, and immutable artifact payloads, with optional Git provenance captured only for authoring traceability and audit.

## Stack Alignment
- Runtime: Python 3.12+
- API surface: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Metadata authority: PostgreSQL for versions, manifests, lifecycle state, provenance metadata, and audit
- Artifact backend: PostgreSQL artifact payload table keyed by immutable digest

## Scope
- Keep `skill_id+version` and artifact digest mapping canonical in PostgreSQL.
- Store artifact bytes in a dedicated PostgreSQL payload table instead of a filesystem or object-store backend.
- Add content-addressed artifact metadata so identical payloads can reuse the same stored row while preserving immutable version bindings.
- Capture optional publish provenance fields such as `repo_url`, `commit_sha`, and `tree_path` without making Git a required dependency for fetch/search flows.
- Preserve immutable HTTP cache semantics (`ETag`, conditional reads) and client ownership boundaries.
- Explicitly reject hybrid runtime storage for the current phase, per `docs/storage-strategy-report.md`.

## Architecture Impact
- Simplifies the storage model by keeping one persistence system while still separating discovery-heavy metadata from fetch-heavy payload rows.
- Preserves deduplication and integrity guarantees while avoiding cross-store consistency risks.
- Keeps Git in the authoring and publish pipeline as optional provenance metadata, not in the synchronous registry read path.

## Deliverables
- Alembic migration for digest-addressed artifact payload tables and optional Git provenance fields.
- Repository and service-layer changes so versions bind immutably to digest-addressed PostgreSQL payload rows.
- API and audit support for normalized provenance metadata on publish and immutable cache headers on fetch.
- Learning note on why split-table PostgreSQL storage is the right tradeoff for current artifact sizes and access patterns.

## Acceptance Criteria
- Publishing identical artifact content across different versions reuses a single stored payload row while preserving distinct immutable version records.
- PostgreSQL remains the source of truth for version metadata, artifact payloads, digest mappings, lifecycle state, and audit history.
- Artifact reads do not require access to a Git repository, working tree, filesystem mirror, or object-store mirror.
- Git provenance metadata is optional and, when supplied, is returned as advisory metadata rather than used as a storage backend or read dependency.
- Immutable read endpoints return stable `ETag` and `Cache-Control` headers derived from the PostgreSQL-stored payload digest.

## Test Plan
- Integration test: publish multiple versions with identical content and verify payload deduplication plus stable digest mapping.
- Integration test: publish with provenance metadata and verify exact fetch returns the stored provenance fields.
- Regression test: artifact fetch continues to work when no Git metadata is present.
- API test: conditional immutable reads return `304` with stable `ETag`.
- Persistence test: split-table PostgreSQL storage honors write-once semantics and digest-addressed lookup contracts.
