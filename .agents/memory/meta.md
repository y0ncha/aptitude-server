# Stable Repo Facts

These facts should stay stable unless the repo intentionally changes direction.

- Canonical docs entrypoint: [docs/README.md](../../docs/README.md)
- Canonical HTTP contract: [docs/project/api-contract.md](../../docs/project/api-contract.md)
- Canonical boundary doc: [docs/project/scope.md](../../docs/project/scope.md)
- Canonical roadmap: [.agents/plans/roadmap.md](../plans/roadmap.md)

## Product Boundary

- `aptitude-server` is the registry backend in the Aptitude ecosystem.
- Resolver/client concerns stay out of the server: prompt interpretation, reranking, final selection, dependency solving, lock generation, and execution planning.
- Server concerns stay data-local: publish, discovery candidate generation, exact dependency reads, exact immutable fetch, lifecycle governance, audit, and observability.

## Frozen Public Route Surface

- `GET /healthz`
- `GET /readyz`
- `GET /metrics`
- `POST /skills/{slug}/versions`
- `POST /discovery`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/versions/{version}`
- `GET /skills/{slug}/versions/{version}/content`
- `PATCH /skills/{slug}/versions/{version}/status`

## Persistence Baseline

- PostgreSQL is the only authoritative runtime store.
- Discovery remains body-free.
- Exact content fetch reads immutable markdown by exact coordinate.
- Content is deduplicated by digest-backed `skill_contents` rows.

## Historical Docs Rule

- `.agents/plans/01-11*.md` and `docs/changelog/01-11*.md` are protected history.
- Existing text in those files is frozen.
- Clarifications must be appended as dated addenda or superseding notes.
