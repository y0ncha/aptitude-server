# Documentation Hub

Use this file as the navigation entrypoint for repository documentation.

The repo has four documentation classes:

- canonical/current docs for the live `aptitude-server` contract and architecture
- operational guides and runbooks for local setup and incident response
- historical milestone plans and changelogs that explain how the repo got here
- drafts/context docs that are useful background but are not the current source of truth

## Canonical / Current Docs

These files describe the live product and engineering baseline:

- [README.md](../README.md): repo entrypoint, frozen route surface, quick start, and docs map
- [docs/project/api-contract.md](project/api-contract.md): canonical public HTTP contract
- [docs/project/scope.md](project/scope.md): server vs resolver/client boundary
- [docs/prd.md](prd.md): current product requirements and success criteria
- [docs/overview.md](overview.md): current product framing and end-to-end system shape
- [docs/schema.md](schema.md): canonical PostgreSQL schema baseline
- [docs/storage-strategy.md](storage-strategy.md): current storage decision and revisit triggers
- [.agents/plans/roadmap.md](../.agents/plans/roadmap.md): milestone sequencing and freeze rules
- [.agents/memory/meta.md](../.agents/memory/meta.md): stable repo facts for agents and future doc work
- [app/README.md](../app/README.md): application package/module index

## Operational Guides and Runbooks

Use these when running or troubleshooting the service:

- [docs/guides/setup-dev.md](guides/setup-dev.md): canonical local setup and observability guide
- [docs/runbooks/README.md](runbooks/README.md): incident/runbook index
- [docs/runbooks/publish-failures.md](runbooks/publish-failures.md)
- [docs/runbooks/discovery-latency-regression.md](runbooks/discovery-latency-regression.md)
- [docs/runbooks/resolution-failures.md](runbooks/resolution-failures.md)
- [docs/runbooks/fetch-failures.md](runbooks/fetch-failures.md)
- [docs/runbooks/governance-denials.md](runbooks/governance-denials.md)
- [docs/runbooks/metrics-scrape-failures.md](runbooks/metrics-scrape-failures.md)
- [docs/runbooks/log-ingestion-failures.md](runbooks/log-ingestion-failures.md)

## Historical Milestones

These files explain delivery history. They are useful, but they are not the canonical source of truth for the current contract.

- [.agents/plans/01-11*.md](../.agents/plans/): protected history for implemented milestones
- [docs/changelog/01-11*.md](changelog/): protected history for delivered milestones
- [.agents/plans/12-15*.md](../.agents/plans/): later milestone planning and follow-on work

History rule:

- Plans and changelogs `01` through `11` are append-only.
- Do not rewrite existing body text in those files.
- Clarifications must be added as dated addenda or superseding notes at the end of the file.

## Drafts and Context

These docs provide background or future-looking ideas. Treat them as context, not as the live contract:

- [docs/project/aptitude-project-high-level-design.md](project/aptitude-project-high-level-design.md)
- [docs/drafts/publisher-server-resolver-architecture.md](drafts/publisher-server-resolver-architecture.md)
- [docs/drafts/semantic-search-architecture.md](drafts/semantic-search-architecture.md)
- [docs/diagrams/aptitude-server-architecture.md](diagrams/aptitude-server-architecture.md)

When a draft conflicts with the canonical docs above, the canonical docs win.
