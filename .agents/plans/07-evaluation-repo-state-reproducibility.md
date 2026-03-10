# Plan 07 — Evaluation and Catalog Snapshot Reproducibility

## Goal
Add evaluation signals and catalog snapshots so metadata quality can evolve while resolver search inputs and exact-read states remain reproducible.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Job execution: APScheduler (MVP), Celery + Redis for scale

## Scope
- Add evaluation run lifecycle and result storage.
- Normalize results to metadata quality scores and advisories.
- Add immutable `catalog_snapshot_id` creation for metadata/index state.
- Expose snapshot read APIs for resolver pinning and audit.
- Explicitly exclude using snapshots to run server-side dependency solving or final candidate selection.

## Architecture Impact
- Connects metadata evolution to reproducibility controls.
- Extends audit trail for evaluation-driven ranking changes.
- Improves cross-service determinism by giving resolver a stable metadata and candidate-retrieval reference.

## Deliverables
- Endpoint: `POST /v1/evaluations/runs`.
- Endpoint: `GET /v1/evaluations/runs/{run_id}`.
- Endpoint: `GET /v1/catalog-snapshots/{catalog_snapshot_id}`.
- Tables for evaluation runs, derived scores, and snapshot manifests.
- Snapshot metadata included in discovery/version responses (for example, snapshot ID or version tag).
- Learning note on mutable derived signals over immutable artifacts.

## Acceptance Criteria
- Evaluation updates derived metadata but not artifact content or checksums.
- Pinned `catalog_snapshot_id` returns stable metadata/discovery views across repeated reads.
- Pinned `catalog_snapshot_id` preserves candidate ordering for repeated search requests against the same query and filters.
- Unpinned latest-state reads can change only via documented evaluation and governance paths.
- Resolver can consume snapshot IDs without any server `resolve` API dependency.

## Test Plan
- Integration test that runs evaluation and verifies metadata update path.
- Determinism test with pinned snapshot across repeated metadata reads and repeated search requests.
- Differential test for latest state vs pinned state behavior.
- Audit test that evaluation and snapshot events are fully recorded.
