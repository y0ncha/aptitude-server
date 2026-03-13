# Plan 09 - Governance, Provenance, and Audit Completion

## Goal
Complete the server-side governance model over the finalized PostgreSQL-backed registry by enforcing lifecycle transitions, trust rules, provenance capture, and audit completeness without expanding the server boundary.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Policy config: pydantic-settings plus environment overrides

## Scope
- Finish lifecycle transitions and visibility rules for `published`, `deprecated`, and `archived`.
- Finish trust-tier enforcement and provenance validation rules at publish and privileged update boundaries.
- Capture provenance metadata such as repository identity, commit SHA, tree path, publisher identity, and trust context as advisory publish-time metadata stored in PostgreSQL.
- Keep provenance advisory only; it must never become a runtime storage or fetch dependency.
- Complete audit coverage for publish, lifecycle, trust-policy, provenance, and privileged governance actions.
- Clean up legacy compatibility tables, columns, or roadmap artifacts that no longer fit the finalized PostgreSQL-only storage and simple public API direction.
- Keep all governance behavior scoped to publish, search visibility, and exact-read policy; do not introduce solving or runtime-selection logic.

## Architecture Impact
- Finishes the governance layer on top of the final registry storage and contract shape.
- Keeps provenance useful for traceability without turning it into a second source of truth.
- Removes stale compatibility baggage before release hardening begins.

## Deliverables
- Policy profile rules covering lifecycle transitions, trust-tier requirements, and provenance validation.
- Final visibility rules for discovery and exact-read behavior across lifecycle states.
- Audit event matrix covering all privileged and mutating governance actions.
- Cleanup plan for legacy persistence and API compatibility artifacts that should not survive into the final architecture.
- Documentation note clarifying that provenance is advisory metadata, not a storage backend or read dependency.

## Acceptance Criteria
- `published`, `deprecated`, and `archived` are enforced consistently for search visibility and exact-read access by documented policy.
- Trust-tier restrictions are enforced on publish and privileged lifecycle or governance actions.
- Provenance metadata is optional, stored in PostgreSQL when present, and returned as advisory metadata only.
- Exact fetch, search, and list behavior remain independent of Git state, filesystem state, and object storage.
- Audit coverage is complete for publish, deprecate, archive, trust-policy changes, provenance capture, and privileged admin actions.
- Legacy compatibility structures still described in older plans are either removed from the roadmap or explicitly marked for deletion as pre-release cleanup.
- The plan does not introduce reranking, dependency solving, lock generation, or execution planning semantics.

## Test Plan
- Policy allow/deny tests for trust-tier and provenance requirements.
- Lifecycle transition tests covering discovery visibility and exact-read behavior for each lifecycle state.
- Integration test verifying exact fetch returns provenance metadata when present and still works when provenance is absent.
- Audit completeness test against the governance event matrix.
- Cleanup regression test confirming legacy compatibility artifacts can be removed without breaking the final publish/search/fetch/governance contract.
