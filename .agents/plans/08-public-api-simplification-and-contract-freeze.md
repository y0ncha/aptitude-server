# Plan 08 - Public API Simplification and Contract Freeze

## Goal
Freeze the final public registry contract around a simple, registry-oriented API surface and remove roadmap commitments to compatibility facades or server namespaces that expose internal service experiments.

## Stack Alignment
- API framework: FastAPI with OpenAPI-first contracts
- Runtime: Python 3.12+
- Validation: Pydantic v2
- Data layer compatibility: SQLAlchemy 2.0 + Alembic

## Scope
- Define the public server surface around registry primitives only: publish, search, list versions, exact fetch, artifact fetch, and lifecycle/governance operations.
- Keep route shape simple and registry-oriented rather than exposing separate public namespaces for internal discovery, fetch, or relationship services.
- Remove `resolution` terminology from the server roadmap and public contract direction.
- Return authored direct dependency declarations and relationship selectors as part of exact version fetch rather than planning a separate relationship read API by default.
- Keep internal service splits allowed where they improve code organization, as long as they do not force separate public route families.
- Assume there is no production compatibility burden; do not preserve deprecated facades or transitional route aliases unless a real external consumer is identified.

## Architecture Impact
- Sharpens the server/client boundary by keeping the public API registry-simple and execution-agnostic.
- Prevents internal service decomposition from leaking into the external contract.
- Reduces long-term API surface area and avoids documenting accidental architecture experiments as durable product decisions.

## Deliverables
- Final OpenAPI direction for simple registry endpoints under the stable skills/governance surface.
- Contract note that exact version fetch includes immutable metadata, integrity fields, artifact identity, provenance metadata when present, and authored direct relationship declarations.
- Removal plan for roadmap commitments to public compatibility facades and public `/resolution/*`-style namespaces.
- Updated acceptance language for search, list, exact fetch, and artifact fetch aligned to the registry docs.

## Acceptance Criteria
- The public roadmap describes a simple registry API and does not introduce public `/resolution/*` namespaces.
- Search remains candidate generation only; the contract does not add reranking, solving, lock generation, or execution planning semantics.
- Exact version fetch is the primary read contract for immutable metadata, direct dependency declarations, selectors, integrity fields, and provenance metadata.
- Artifact content remains a separate immutable-read endpoint with cache-friendly headers.
- Any discovery/fetch/relationship split is described as an internal service design choice, not as required public route structure.
- No compatibility facade or deprecation path is planned unless an actual consumer requires it.

## Test Plan
- OpenAPI contract test for the final publish/search/list/fetch/governance route set.
- Contract test verifying exact version fetch includes authored direct dependency and relationship declaration data.
- Regression test ensuring artifact bytes are not inlined into exact metadata fetch.
- Boundary test verifying the documented API surface stays registry-only and does not expose solve or plan semantics.
