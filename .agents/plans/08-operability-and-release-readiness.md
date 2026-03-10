# Plan 08 — Operability and Release Readiness

## Goal
Harden the repository service for reliable operation, auditing, and repeatable deployment.

## Stack Alignment
- Runtime: Python 3.12+
- API and contracts: FastAPI + Pydantic v2
- Data layer: SQLAlchemy 2.0 + Alembic
- Quality gates: pytest, ruff, mypy, coverage thresholds

## Scope
- Complete audit event matrix across publish, fetch, search, lifecycle, and evaluation flows.
- Add structured logs and correlation IDs.
- Add metrics endpoint and baseline instrumentation.
- Add Docker packaging and CI quality gates.
- Add SLO instrumentation aligned to `prd.md` for exact-read latency, discovery search latency, and fetch reliability.

## Architecture Impact
- Strengthens observability and audit layer.
- Adds deployment and quality infrastructure without changing domain invariants.
- Prepares server contracts for independent resolver release trains.

## Deliverables
- Structured logging conventions and correlation ID propagation.
- Metrics endpoint and core counters and timers.
- Dockerfile and local run instructions.
- CI pipeline stages for unit, integration, lint, type-check, and coverage threshold.
- Operational runbook for publish/read/governance incident response.
- Learning note on reliability and observability tradeoffs.

## Acceptance Criteria
- End-to-end repository flow is observable with logs, metrics, and audit trace.
- CI blocks merges on failing quality gates.
- Containerized service starts and runs migrations on startup path.
- 100% of publish/deprecate/archive actions emit auditable events.
- Read SLO instrumentation is present for `GET /skills/{id}/{version}` p95 <= 150 ms.
- Search latency instrumentation is present for `GET /skills/search` so agent workflows can treat discovery as an interactive primitive.
- Artifact fetch reliability instrumentation is present for monthly target >= 99.9%.

## Test Plan
- End-to-end integration test for publish -> fetch -> search -> lifecycle update.
- `pytest` suite in CI with coverage and deterministic integration checks.
- Smoke test in containerized environment.
- Audit completeness test against the event matrix.
- Performance and load test validating exact-read latency and discovery search latency targets.
