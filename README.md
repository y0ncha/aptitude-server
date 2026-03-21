# aptitude-server

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-6E56CF?style=for-the-badge&logo=uv&logoColor=white)
![FastAPI](https://img.shields.io/badge/fastapi-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/sqlalchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=111111)
![Docker](https://img.shields.io/badge/docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)
![Loki](https://img.shields.io/badge/loki-F2CC0C?style=for-the-badge&logo=grafana&logoColor=111111)
[![DeepWiki](https://img.shields.io/badge/Ask-DeepWiki-0A66C2?style=for-the-badge&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAsVBMVEVHcEwmWMYZy38Akt0gwZoSaFIbYssUmr4gwJkBlN4WbNE4acofwZkBj9k4aMkBk94WgM0bsIM4aMkewJc2ZMM3Z8cbvIwYpHsewJYAftgBkt0fvpgBkt0cv44cv5wzYckAjtsCk90pasUboXsgwJkfwpYfwJg4aMoct44yXswAkd0BkN84Z8cBktwduZIjcO85lM4hwZo5acoBleA6a88iyaABmOQ8b9QhxZ0CnOoizaOW4DOvAAAAMHRSTlMAKCfW%2FAgWA%2F7%2FDfvMc9j7MU%2Frj3XBcRW%2FJMbe7kUxjI%2FlUzzz6tPQkJ%2BjVmW1oeulmmslAAAByUlEQVQ4y32Tia6jIBSGUVFcqliXtlq73rm3d50ERNC%2B%2F4PNQetoptMeE0PgC%2F9%2FFhCaBSH9Hz2J%2BONgPDl2DolSUWY%2FPL8oEQRCfPxHpFc3Ah5wHoiI6I05NXgjAOgQF3Jn1Dlo4XMPDDes09UE2d%2BREvl3lijBg4CrHNmrbcM2u9u5nwsRcAFfFHFY5sZ607Yua3GqpQiKE6G9cZHZThblZ4T2mLnMxde3ATASMUj72o0Pbs1fADDcLHqAjEDugJ3lC%2BztMGYTADcoLaFyH%2B02DP9%2BWS4ahrXE4laALFKcq8vZfscNY8312mxfr27bLJZjnsYhSDIHmUxLu9h9N%2Fep%2B7pazwoZQw%2B1Nwi33epu7c2p8RooeqCdAHMGoOJIq3CUwIMEniRIaHVe3ZVnO2Vgsh1MstEkQUXVUc%2BjXfk3zbemxS6%2BpQmlPtUeALJ8VKj4JHvAelBqFFdSS3h1SPzQKr%2F%2BaRa0%2B0cCIWtJLauG5U%2FfbgyG01uiNqQhyzA8ddKj1OvK28AsZyN3DKE4X6AEWrU1jJx9N7RFpdPxpHU%2FtMOQG9SjfTp3Yz8KgRVKpfx88Dqhpseq606h%2F%2Bzxfh6LJ8eEDKWbxx9XEDwqzP1SVgAAAABJRU5ErkJggg%3D%3D)](https://deepwiki.com/y0ncha/aptitude-server)
![Last Commit](https://img.shields.io/github/last-commit/y0ncha/aptitude-server?style=for-the-badge)

`aptitude-server` is the registry backend in the Aptitude ecosystem. It stores
immutable skill metadata, digest-addressed markdown content, lifecycle state,
provenance snapshots, and audit data in PostgreSQL so callers can publish exact
versions, discover candidate slugs, read direct authored dependencies, and
fetch immutable metadata/content without crawling the full catalog.

## Overview

`aptitude-server` is the authoritative catalog for Aptitude skills.

- It owns immutable publication, discovery candidate generation, exact
  dependency reads, exact metadata/content fetch, lifecycle governance, audit,
  and operational telemetry.
- It does not own prompt interpretation, reranking, final selection,
  dependency solving, lock generation, or execution planning. Those stay in the
  resolver/client layer.
- It uses PostgreSQL as the only authoritative runtime store, with a deliberate
  split between discovery-facing metadata/search models and exact-fetch content
  storage.

The design target is registry-first and execution-agnostic: keep the server
fast, cacheable, and deterministic, while the resolver/client stays responsible
for runtime decisions.

## System Design

```mermaid
flowchart LR
    Publisher["Publisher / CI"]
    Resolver["Resolver / MCP / CLI"]
    Ops["Ops / observability"]

    subgraph Server["aptitude-server"]
        direction TB
        Interface["Interface layer<br/>publish, discovery, resolution, fetch"]
        Core["Core services<br/>registry, discovery, resolution, fetch, governance"]
        Adapters["Persistence + audit adapters"]
    end

    Storage["Registry storage<br/>versions, metadata, content,<br/>selectors, search, audit"]

    Publisher -->|publish / lifecycle writes| Interface
    Resolver <-->|discovery / resolution / exact fetch| Interface
    Ops <-->|health / metrics / logs / runbooks| Interface
    Interface --> Core
    Core --> Adapters
    Adapters <-->|reads / writes| Storage
```

Design rules:

- Server owns data-local work; resolver/client owns decision-local work.
- Discovery returns ordered slug candidates only.
- Resolution returns direct authored `depends_on` selectors only.
- Exact fetch stays coordinate-based and immutable.
- Historical milestone docs may mention older route names; the canonical
  contract lives in [docs/project/api-contract.md](docs/project/api-contract.md).

### Why Discovery, Resolution, and Fetch Are Separate

The split is deliberate. These are different workloads, and collapsing them
into one generic read API would mix hot search traffic with exact immutable
reads and dependency lookups.

| Surface | Request Shape | Response Shape | Primary Backing Data | Load Profile | Why It Stays Separate |
| --- | --- | --- | --- | --- | --- |
| Discovery | Loose query text and optional tags | Ordered candidate slugs | `skill_search_documents` and discovery ranking inputs | Highest fan-out, index-heavy, read-optimized | Keeps search traffic away from large immutable content reads. |
| Resolution | Exact `slug` + `version` | Direct authored relationship selectors | `skill_relationship_selectors` | Deterministic, graph-local, lightweight | Lets dependency solving read only declared edges, not whole skill payloads. |
| Fetch | Exact `slug` + `version` | Immutable metadata or markdown content | `skill_versions`, `skill_metadata`, `skill_contents` | Payload-heavy, cache-friendly, exact reads | Isolates full object retrieval from search and dependency workloads. |

This separation gives clear load isolation:

- Discovery can scale around search indexes and ranking without dragging full
  markdown bodies through the hot path.
- Resolution stays cheap and predictable because it reads only published
  selector edges needed for dependency solving.
- Fetch can optimize for immutable payload delivery, caching, and integrity
  checks without affecting search latency.

In practice, this means one noisy workload does not distort the others.
Discovery traffic does not force content reads, and content reads do not bloat
dependency-resolution paths.

## Frozen Route Surface

The public HTTP baseline is:

- `GET /healthz`
- `GET /readyz`
- `GET /metrics`
- `POST /skills/{slug}/versions`
- `POST /discovery`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/versions/{version}`
- `GET /skills/{slug}/versions/{version}/content`
- `PATCH /skills/{slug}/versions/{version}/status`

Use [docs/project/api-contract.md](docs/project/api-contract.md) as the
canonical contract. Historical milestone docs may mention pre-freeze routes;
treat those as history only.

## Boundary

- Server owns data-local work: publish, discovery candidate generation, exact
  dependency reads, exact fetch, lifecycle governance, audit, and
  Prometheus-compatible metrics.
- Resolver/client owns decision-local work: prompt interpretation, reranking,
  final selection, dependency solving, lock generation, and execution planning.

In practice, `aptitude-server` behaves like a package registry, while the
resolver/client behaves like the package manager/runtime planner.

## Skill Schema

The skill schema is intentionally split so discovery stays body-free while exact
fetch still returns immutable markdown.

| Schema Area | Backing Table | Purpose | Returned By |
| --- | --- | --- | --- |
| Metadata | `skill_metadata` | Stores the structured, queryable skill description used for discovery and exact metadata reads. | `GET /skills/{slug}/versions/{version}` |
| Content | `skill_contents` | Stores the immutable markdown body, checksum digest, and size metadata for exact content fetches. | `GET /skills/{slug}/versions/{version}/content` |
| Version Binding | `skill_versions` | Binds one immutable version to one metadata row and one content row, plus lifecycle/trust/provenance state. | Publish + exact metadata reads |
| Relationship Selectors | `skill_relationship_selectors` | Preserves authored `depends_on` and other selector families exactly as published. | `GET /resolution/{slug}/{version}` |
| Search Projection | `skill_search_documents` | Derived discovery read model used for lexical search and deterministic candidate ordering. | `POST /discovery` |

### Metadata Fields

| Field | Stored In | Role |
| --- | --- | --- |
| `name` | `skill_metadata` | Human-readable display name returned in exact metadata reads and used in discovery matching. |
| `description` | `skill_metadata` | Canonical short summary used for discovery and exact metadata responses. |
| `tags` | `skill_metadata` | Primary categorical discovery filters. |
| `headers` | `skill_metadata` | Flexible structured metadata that still belongs in the immutable metadata envelope. |
| `inputs_schema` / `outputs_schema` | `skill_metadata` | Structured contract fragments for callers that need input/output shape information. |
| `token_estimate` / `maturity_score` / `security_score` | `skill_metadata` | Numeric ranking/filtering inputs for discovery and downstream resolver scoring. |

### Content Fields

| Field | Stored In | Role |
| --- | --- | --- |
| `raw_markdown` | `skill_contents` | Canonical immutable markdown body. |
| `storage_size_bytes` | `skill_contents` | Exact content size used for diagnostics and response metadata. |
| `checksum_digest` | `skill_contents` | Digest-backed content identity for integrity and caching. |
| `checksum_digest` | `skill_versions` | Version-level checksum returned in exact metadata responses. |

## Quick Start

Requirements:

- Python `3.12+`
- [`uv`](https://docs.astral.sh/uv/)
- Docker

Local dev:

```bash
make db-up
uv venv
source .venv/bin/activate
uv sync --extra dev
export DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/aptitude"
export AUTH_TOKENS_JSON='{"reader-token":["read"],"publisher-token":["read","publish"],"admin-token":["read","publish","admin"]}'
make migrate-up
make run
```

Local URLs:

- API + Swagger docs: `http://127.0.0.1:8000/docs`
- Metrics: `http://127.0.0.1:8000/metrics`

For the full setup flow, environment options, observability profile, and Loki
verification steps, use [docs/guides/setup-dev.md](docs/guides/setup-dev.md).

## Operability

- `GET /metrics` is the operational scrape endpoint.
- The server echoes `X-Request-ID` on every response so requests can be stitched
  across logs, metrics, and audit rows.
- `make observability-up` starts the local Prometheus, Grafana, and Loki stack.

## Documentation

- [docs/README.md](docs/README.md): documentation hub
- [docs/project/api-contract.md](docs/project/api-contract.md): canonical HTTP contract
- [docs/project/scope.md](docs/project/scope.md): server vs resolver/client boundary
- [docs/prd.md](docs/prd.md): product requirements
- [docs/schema.md](docs/schema.md): PostgreSQL schema baseline
- [docs/storage-strategy.md](docs/storage-strategy.md): storage decision
- [docs/runbooks/README.md](docs/runbooks/README.md): runbook index
