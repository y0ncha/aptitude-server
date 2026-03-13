# Plan 10 - Operability and Release Readiness

## Goal
Harden `aptitude-server` for repeatable deployment and reliable operation after the storage model, public API, and governance behavior are finalized.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Quality gates: pytest, ruff, mypy, coverage thresholds

## Scope
- Add structured logs, correlation IDs, and audit trace stitching across publish, search, fetch, artifact fetch, and lifecycle/governance paths.
- Add metrics, dashboards, alerts, and SLO instrumentation for the final registry API and PostgreSQL-only storage model.
- Add Docker packaging, startup/run instructions, and CI quality gates.
- Add runbooks for incidents on publish, search, exact fetch, artifact fetch, lifecycle, and governance operations.
- Validate performance and reliability against the finalized API and storage shape from Plans 07-09 rather than against transitional routes or storage semantics.
- Keep all operability assumptions PostgreSQL-only and registry-only.

## Architecture Impact
- Adds deployment and observability infrastructure without reopening product or storage decisions.
- Makes the final registry contract measurable and supportable.
- Prevents premature hardening of transitional APIs or discarded persistence patterns.

## Deliverables
- Structured logging conventions and correlation ID propagation.
- Metrics endpoint plus counters, timers, and error-rate tracking for final registry operations.
- Dashboards and alerts for publish, search, exact fetch, artifact fetch, and governance flows.
- Dockerfile and local/prod run instructions.
- CI pipeline stages for unit, integration, lint, type-check, and coverage gates.
- Operational runbooks aligned to the final PostgreSQL-only architecture and final public route set.

## Acceptance Criteria
- End-to-end registry flows are observable through logs, metrics, and audit trace data.
- CI blocks merges on failing quality gates.
- Containerized startup and migration flow work against the final service shape.
- Search and exact fetch SLO instrumentation aligns with the KPIs in `docs/prd.md`.
- Artifact fetch reliability instrumentation exists for the final immutable content endpoint.
- Runbooks and alerts assume PostgreSQL-only storage and never reference filesystem or object-store artifact backends.
- Operability work does not introduce or preserve transitional public API namespaces.

## Test Plan
- End-to-end integration test covering publish -> search -> exact fetch -> artifact fetch -> lifecycle update.
- CI smoke test in containerized environment.
- Audit/log correlation test for a complete registry request path.
- Performance/load validation for search and exact fetch on the finalized route set.
- Alerting and metrics sanity test for publish failures, exact-read failures, and search latency regression.
