# Plan 10 - Governance, Provenance, and Audit Completion

## Goal
Complete the governance model over the finalized PostgreSQL-backed registry while assuming the hard-cut public contract from Plans 07-09: discovery candidates, exact first-degree resolution, exact metadata fetch, exact content fetch, and governed write operations.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Policy config: pydantic-settings plus environment overrides

## Scope
- Finish lifecycle transitions and visibility rules for `published`, `deprecated`, and `archived`.
- Enforce trust-tier requirements and provenance validation at publish and privileged update boundaries.
- Apply governance consistently across:
  - `POST /discovery` visibility
  - `GET /resolution/{slug}/{version}` exact-read policy
  - `GET /skills/{slug}/versions/{version}` exact-read policy
  - `GET /skills/{slug}/versions/{version}/content` exact-read policy
- Apply governance inside the existing publish, discovery, resolution, exact fetch, and lifecycle endpoints; do not add provenance, audit, or policy-specific public endpoint families.
- Capture provenance metadata such as repository identity, commit SHA, tree path, publisher identity, and trust context as advisory publish-time metadata stored in PostgreSQL.
- Keep provenance advisory only; it must never become a runtime dependency for discovery, resolution, or fetch behavior.
- Complete audit coverage for publish, lifecycle, trust-policy, provenance, and privileged governance actions.
- Remove stale persistence and API artifacts that no longer fit the hard-cut contract.

## Architecture Impact
- Finishes the governance layer on top of the simplified public API and PostgreSQL-only storage.
- Keeps provenance useful for traceability without letting it leak into runtime data ownership.
- Removes stale public-contract baggage before release hardening.

## Deliverables
- Policy profile rules covering lifecycle transitions, trust-tier requirements, and provenance validation.
- Final visibility rules for discovery, resolution, and exact fetch behavior across lifecycle states.
- Audit event matrix covering all privileged and mutating governance actions.
- Governance note clarifying that policy enforcement lives inside the existing endpoint set rather than behind additional public routes.
- Cleanup plan for persistence or API artifacts that only existed for removed routes or compatibility semantics.
- Documentation note clarifying that provenance is advisory metadata, not a read dependency or alternate storage backend.

## Acceptance Criteria
- `published`, `deprecated`, and `archived` are enforced consistently for discovery visibility and exact-read access.
- Trust-tier restrictions are enforced on publish and privileged governance actions.
- Provenance metadata is optional, stored in PostgreSQL when present, and returned as advisory metadata only.
- Discovery, resolution, and fetch behavior remain independent of Git state, filesystem state, and object storage.
- Audit coverage is complete for publish, deprecate, archive, trust-policy changes, provenance capture, and privileged admin actions.
- Governance completion does not add new public endpoint families or specialized variants of discovery, resolution, or fetch.
- Stale compatibility artifacts are removed from the roadmap and final governance direction.

## Test Plan
- Policy allow/deny tests for trust-tier and provenance requirements.
- Lifecycle transition tests covering discovery visibility plus resolution and fetch access for each lifecycle state.
- Integration test verifying provenance metadata is returned when present and ignored cleanly when absent.
- Audit completeness test against the governance event matrix.
- Cleanup regression test confirming removed-route artifacts do not survive into the final governed contract.

## Implementation Notes - 2026-03-15
- Publisher-collected advisory provenance now supports optional `publisher_identity`; the server normalizes and validates provenance, persists it immutably on `skill_versions`, and derives `trust_context` from stored trust tier plus the active policy profile.
- Exact metadata fetch returns enriched advisory provenance when present, while discovery, resolution, and raw content fetch remain provenance-independent and continue to avoid Git/filesystem/object-storage dependencies.
- Successful publish and lifecycle audits now commit transactionally with the authoritative mutation, while discovery, exact reads, and denied governance actions use the standalone audit recorder.
- The audit matrix now covers successful and denied publish, successful and denied lifecycle updates, discovery, exact resolution/metadata/content reads, and denied exact reads for hidden lifecycle states.
- Contract docs, DTO examples, module READMEs, and stale unit tests were updated to match the publisher/server/resolver split and the frozen public route families.
