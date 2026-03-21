# app.interface module

Server interface boundary.

## Purpose

Hosts externally exposed API boundaries and request/response contracts.

## Key Modules

- `api/`: HTTP routers for health and skill catalog endpoints.
- `dto/`: Service-specific DTO modules for publish, discovery, resolution, status, and exact metadata fetch contracts.
- `__init__.py`: package marker.

## Boundary Rule

Interface code depends on core services/contracts and must not bypass core
behavior by calling persistence adapters directly.
Core skill-domain imports should target `app.core.skills.*`; interface code
should not assume the skill-domain modules live flat under `app.core`.
Routes for `/healthz`, `/readyz`, and `/metrics` may depend on
`app.observability.*` helpers, but the HTTP boundary still stays in
`app.interface`.
Publisher-supplied provenance remains part of the publish contract only; the
interface must not introduce provenance-specific route families or make read
paths depend on publisher-side state.
Exact metadata responses expose summary text only through
`metadata.description`; `content` includes checksum and size metadata only.
