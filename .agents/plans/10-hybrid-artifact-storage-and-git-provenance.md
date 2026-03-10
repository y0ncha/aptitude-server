# Plan 10 - Hybrid Artifact Storage and Git Provenance

## Goal
Keep PostgreSQL authoritative for registry metadata while moving immutable artifact payloads to content-addressed filesystem or object storage, with optional Git provenance captured for authoring traceability rather than runtime reads.

## Stack Alignment
- Runtime: Python 3.12+
- API surface: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Metadata authority: PostgreSQL for versions, manifests, digest mappings, lifecycle state, provenance metadata, and audit
- Artifact backend: local filesystem in MVP, object storage later, both addressed by immutable digest-backed keys

## Scope
- Keep `skill_id+version` and digest mapping canonical in PostgreSQL.
- Store artifact bytes outside PostgreSQL in immutable filesystem layout, with an object-storage adapter planned as a compatible backend.
- Add content-addressed artifact metadata so identical payloads can reuse the same stored blob while preserving immutable version bindings.
- Capture optional publish provenance fields such as `repo_url`, `commit_sha`, and `tree_path` without making Git a required dependency for fetch/search flows.
- Preserve immutable HTTP cache semantics (`ETag`, conditional reads) and resolver ownership boundaries.

## Architecture Impact
- Simplifies the storage model by separating query-heavy metadata from blob storage concerns.
- Preserves deduplication and integrity guarantees without making PostgreSQL carry artifact payload IO.
- Keeps Git in the authoring and publish pipeline, not in the synchronous registry read path.

## Deliverables
- Alembic migration for digest-addressed artifact metadata and optional Git provenance fields.
- Repository and service-layer changes so versions bind immutably to digest-addressed artifact references rather than in-database blobs.
- Filesystem artifact layout updated to support digest-addressed deduplication and backend abstraction for later object storage.
- API and audit support for provenance metadata on publish and immutable cache headers on fetch.
- Learning note on blob-store versus database responsibilities and why Git remains outside the runtime storage boundary.

## Acceptance Criteria
- Publishing identical artifact content across different versions reuses a single stored blob reference while preserving distinct immutable version records.
- PostgreSQL remains the source of truth for version metadata, digest mappings, lifecycle state, and audit history.
- Artifact reads do not require access to a Git repository.
- Git provenance metadata is optional and, when supplied, is returned as metadata rather than used as a storage backend.
- Immutable read endpoints return stable `ETag` and `Cache-Control` headers independent of the underlying blob backend.

## Test Plan
- Integration test: publish multiple versions with identical content and verify blob deduplication plus stable digest mapping.
- Integration test: publish with provenance metadata and verify exact fetch returns the stored provenance fields.
- Regression test: artifact fetch continues to work when no Git metadata is present.
- API test: conditional immutable reads return `304` with stable `ETag`.
- Adapter test: filesystem backend honors write-once semantics and digest-addressed lookup contracts.
