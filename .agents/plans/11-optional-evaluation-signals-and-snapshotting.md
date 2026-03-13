# Plan 11 - Optional Evaluation Signals and Snapshotting

## Goal
Leave room for post-launch discovery improvements through derived evaluation signals, while explicitly treating snapshot APIs and latest-state reproducibility features as optional follow-up work rather than baseline roadmap commitments.

## Positioning
This milestone is post-launch and optional. It is not part of MVP readiness, v1 contract freeze, or release hardening.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Background execution: APScheduler for simple runs, with queue-backed workers only if scale proves necessary

## Scope
- Add derived evaluation signals only if they materially improve discovery quality over the final baseline search implementation.
- Keep evaluation outputs limited to mutable derived metadata used for advisory retrieval and ranking explanations.
- Treat catalog snapshots as deferred and trigger-based, not as a default product commitment.
- Introduce snapshot APIs only if real client workflows need stable latest-state discovery views that exact version pins and client lock outputs do not already solve.
- Keep all evaluation and snapshot work separate from canonical artifact storage, digest bindings, and immutable exact-read contracts.
- Preserve the hard server/client boundary: no server-side solving, final candidate selection, lock generation, or execution planning.

## Trigger Criteria
- Search quality regressions or ambiguity cannot be addressed with existing metadata and deterministic base ranking alone.
- Real consumers need auditable, pinned latest-state discovery views in addition to immutable exact version coordinates.
- Operational evidence shows evaluation-derived metadata changes are frequent enough that snapshotting materially improves debugging, reproducibility, or audit workflows.

## Architecture Impact
- Keeps future discovery enhancements decoupled from core registry correctness.
- Prevents speculative reproducibility mechanisms from becoming premature MVP obligations.
- Protects exact immutable fetch semantics from being entangled with mutable derived metadata.

## Deliverables
- Derived evaluation run model and result storage only if trigger criteria are met.
- Discovery response support for evaluation-derived explanation fields only when signals are enabled.
- Optional snapshot design note describing when pinned latest-state views are justified and when they are unnecessary.
- Documentation note stating that exact version pins and client-generated locks remain the default reproducibility mechanism.

## Acceptance Criteria
- If implemented, evaluation updates derived metadata only and never mutates artifact payloads, digest mappings, or version identity.
- Snapshot APIs are not added unless one or more trigger criteria are explicitly satisfied.
- Exact immutable fetch remains independent of evaluation state and snapshot state.
- The milestone remains clearly marked optional and post-launch in roadmap and plan language.
- No part of the plan introduces server-side reranking authority, dependency solving, lock generation, or execution planning.

## Test Plan
- Integration test verifying evaluation-derived metadata updates do not affect immutable artifact fetch behavior.
- Determinism test proving exact version fetch stays stable regardless of evaluation state.
- If snapshots are introduced, repeated reads against a pinned snapshot return stable discovery results for the same query/filter set.
- Audit test covering evaluation and snapshot events when those features are enabled.
