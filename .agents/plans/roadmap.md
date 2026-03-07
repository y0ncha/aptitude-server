# Aptitude Roadmap

## Goal
Deliver a production-ready, deterministic skill server in Python/FastAPI through incremental, testable milestones.

## Alignment Sources
- Scope boundary and ownership: [`docs/scope.md`](../../docs/scope.md)
- Server requirements and KPIs: [`docs/repository-prd.md`](../../docs/repository-prd.md)

## Platform Defaults
- Database: PostgreSQL (primary from the first milestone).
- Migrations: versioned SQL migrations (up/down), no manual schema changes.
- Search: PostgreSQL-native indexing and full-text capabilities.

## Boundary Guardrails
- This roadmap covers `aptitude-server` only.
- MCP/CLI prompt interfaces, plugin machines, and runtime execution planning belong to `aptitude-resolver` and are out of scope here.
- Server remains execution-agnostic and exposes governed APIs for publish, fetch, resolve, and reports.

## Milestones
1. `01-foundation-service-skeleton.md`
2. `02-immutable-skill-registry.md`
3. `03-deterministic-dependency-resolution.md`
4. `04-repository-api-contract-v1.md`
5. `05-metadata-search-ranking.md`
6. `06-policy-conflict-governance.md`
7. `07-evaluation-repo-state-reproducibility.md`
8. `08-operability-and-release-readiness.md`

## PRD Phase Mapping
- `MVP` (repository-prd): milestones 01-04.
- `v1.1` (repository-prd): milestones 05-06.
- `v2.0` prep (repository-prd): milestones 07-08.
- Optional RAG retrieval remains disabled by default and requires a new follow-up plan once benchmark gates are defined.

## Roadmap Rules
- Plans are append-only.
- Completed plans are never renamed or renumbered.
- New scope changes create a new numbered plan file.
