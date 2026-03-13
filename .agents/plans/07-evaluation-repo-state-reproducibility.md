# Plan 07 - Canonical PostgreSQL Storage Finalization

## Goal
Finalize the registry on a single runtime storage architecture: PostgreSQL is the only authoritative store for skill metadata, digest bindings, immutable artifact payloads, lifecycle state, provenance metadata, and audit references.

This plan replaces transitional storage thinking with a hard cut. Because there is no production database or production consumer contract to preserve, implementation should overwrite in-flight persistence direction instead of layering compatibility structures on top.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Database: PostgreSQL as the only runtime persistence system

## Scope
- Finalize PostgreSQL-only split storage for discovery-facing metadata and exact-fetch payload rows.
- Keep immutable `skill_id + version` records bound to one PostgreSQL-stored digest-addressed payload.
- Preserve digest-based integrity semantics, immutable overwrite rejection, and HTTP cache identity via `ETag`.
- Keep provenance metadata in PostgreSQL as publish-time advisory metadata only.
- Remove filesystem-era and other transitional persistence concepts from the plan and target architecture.
- Prefer direct replacement of in-flight schema and repository shape over compatibility layering, mirror columns, or bridge tables that exist only to ease a production migration.
- Keep discovery and exact fetch separately optimizable through schema, service, and query-path design within one transactional system.

## Architecture Impact
- Freezes the storage decision already supported by `docs/prd.md` and `docs/storage-strategy-report.md`.
- Removes ambiguity about runtime dependencies: no filesystem storage, no object storage, no Git-backed reads, no hybrid persistence model.
- Reduces long-term debt by treating transitional persistence artifacts as disposable, not as permanent compatibility surface.

## Deliverables
- Canonical schema definition for PostgreSQL-only artifact payloads, digest bindings, version metadata, lifecycle state, and provenance fields.
- Cleanup plan for persistence artifacts that exist only because earlier milestones were framed as a migration instead of a replacement.
- Repository and service expectations for publish, exact fetch, discovery, and artifact fetch against the final PostgreSQL-only model.
- Documentation note clarifying that overwrite-in-place of in-flight design is required for the current pre-production phase.

## Acceptance Criteria
- PostgreSQL is the only planned runtime persistence layer for artifact payloads, metadata, digest mappings, provenance metadata, and audit references.
- Each immutable `skill_id + version` maps to exactly one digest-backed PostgreSQL payload row and cannot be overwritten.
- Identical artifact payloads published under different versions reuse a single digest-addressed PostgreSQL payload row.
- Discovery paths do not need to touch payload storage for routine list and search queries.
- Exact fetch and artifact fetch do not require any filesystem path, Git checkout, local mirror, or object-store bucket.
- Immutable reads keep stable digest-derived `ETag` semantics and conditional-read support.
- The plan does not preserve transitional storage structures solely for migration convenience.

## Test Plan
- Integration test: publish identical payloads across versions and verify digest deduplication with immutable version bindings.
- Integration test: publish distinct payloads and verify distinct digest rows and exact fetch behavior.
- API test: immutable reads return stable `ETag` values and support `If-None-Match`.
- Regression test: duplicate publish to the same `skill_id + version` remains rejected without mutating existing rows.
- Persistence test: discovery/list queries remain payload-free by default.
