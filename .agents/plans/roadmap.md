# Aptitude Roadmap

## Goal
Deliver a production-ready, PyPI-like immutable registry service (`aptitude-server`) in Python/FastAPI through incremental, testable milestones.

## Alignment Sources
- Scope boundary and ownership: [`docs/scope.md`](../../docs/scope.md)
- Server requirements and KPIs: [`docs/prd.md`](../../docs/prd.md)
- Resolver ownership and dependency-solving responsibilities are out of scope for this repository and tracked in the resolver repository.

## Platform Defaults
- Database: PostgreSQL (primary from the first milestone).
- Migrations: versioned SQL migrations (up/down), no manual schema changes.
- Search: PostgreSQL-native indexing and full-text capabilities.

## Boundary Guardrails
- This roadmap covers `aptitude-server` only.
- Server owns data-local retrieval work: publish, exact fetch, list, discovery indexes, and metadata/description search candidate generation.
- Resolver owns decision-local work: MCP/CLI prompt interfaces, prompt interpretation, reranking, final candidate selection, dependency solving, lock generation, plugin orchestration, and execution planning.
- Server remains execution-agnostic and exposes governed APIs for publish, fetch, list, discovery, lifecycle, and provenance.
- Server contracts are manifest/metadata/integrity envelopes; the server does not return canonical solved bundles.
- Server search ranking remains advisory; resolver choice and lock output remain authoritative.

## Milestones
1. `01-foundation-service-skeleton.md`
2. `02-immutable-skill-registry.md`
3. `03-deterministic-dependency-resolution.md` (legacy filename; scope is dependency metadata contracts, not server-side solving)
4. `04-repository-api-contract-v1.md`
5. `05-metadata-search-ranking.md`
6. `06-policy-conflict-governance.md`
7. `07-evaluation-repo-state-reproducibility.md` (rewritten scope: canonical PostgreSQL storage finalization)
8. `08-operability-and-release-readiness.md` (rewritten scope: public API simplification and contract freeze)
9. `09-postgres-content-addressed-artifact-cache.md` (rewritten scope: governance, provenance, and audit completion)
10. `10-postgres-only-artifact-storage-and-provenance.md` (rewritten scope: operability and release readiness)
11. `11-discovery-resolution-fetch-service-split.md` (rewritten scope: optional post-launch evaluation signals and snapshotting)

## PRD Phase Mapping
- `MVP` (prd): milestones 01-04.
- `v1.1` (prd): milestones 05-06.
- `v2.0` prep (prd): milestones 07-09.
- `Release readiness`: milestone 10.
- `Post-launch optional discovery enhancements`: milestone 11.
- Resolver-specific initiatives (prompt interpretation, deterministic solving, reranking, plugin chains, and lock replay) are tracked in resolver planning and are out of scope for this roadmap.

## Roadmap Rules
- Roadmap numbering is append-only.
- Plan filenames and titles may be corrected before implementation when the existing milestone framing is architecturally wrong.
- Completed plans are never renamed or renumbered.
- New scope changes create a new numbered plan file.
