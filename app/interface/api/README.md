# app.interface.api module

HTTP API routers for the service.

## Purpose

Defines FastAPI routes, request validation, response schemas, and error
translation for the service's public HTTP contract. This package is the thin
adapter layer between FastAPI and core services.

## Key Files

- `health.py`: liveness/readiness endpoints (`/healthz`, `/readyz`).
- `discovery.py`: body-based candidate lookup route at `/discovery`.
- `resolution.py`: exact first-degree dependency read route at
  `/resolution/{slug}/{version}`.
- `fetch.py`: exact immutable metadata and markdown fetch routes under
  `/skills/{slug}/versions/{version}`.
- `skills.py`: publish and lifecycle-status routes.
- `errors.py`: stable JSON error envelope helpers and FastAPI exception
  handlers.
- `response_docs.py`: shared OpenAPI response fragments reused across route files.
- `skill_api_support_publish.py`: publish request-to-core command translation.
- `skill_api_support_fetch.py`: exact metadata response mapping.
- `skill_api_support_resolution.py`: dependency resolution response mapping.
- `skill_api_support_lifecycle.py`: lifecycle-status response mapping.
- `skill_api_support.py`: compatibility re-export for the split mapper modules.
- `__init__.py`: package marker.

## Route Surface

- `GET /healthz`: process liveness probe.
- `GET /readyz`: dependency readiness probe with a `503` response when the
  service is not ready.
- `POST /discovery`: discovery-only candidate lookup returning ordered slug
  candidates.
- `GET /resolution/{slug}/{version}`: direct authored `depends_on`
  declarations for one immutable version.
- `GET /skills/{slug}/versions/{version}`: immutable metadata fetch for one
  exact coordinate.
- `GET /skills/{slug}/versions/{version}/content`: immutable markdown fetch for
  one exact coordinate.
- `POST /skills/{slug}/versions`: immutable skill version publication.
- `PATCH /skills/{slug}/versions/{version}/status`: lifecycle-status transition
  for one immutable version.

## Notes

Routers should stay thin. They validate HTTP input, call a core service, and
translate results into public DTOs without embedding business policy.
Routers that depend on the skill-domain core should import from
`app.core.skills.*` rather than assuming a flat `app.core` module layout.
`errors.py` owns the public error envelope so request validation failures,
policy violations, and explicit API errors share one JSON shape.
The `skill_api_support_*.py` modules are split by API surface so route handlers
reuse mapping code without collecting every conversion function in one file.
`response_docs.py` centralizes repeated OpenAPI response fragments so request
validation and exact-version-not-found responses stay consistent across routes.
`POST /skills/{slug}/versions` requires `intent=create_skill|publish_version`
so the API can distinguish first publication from publication to an existing
skill slug.
`POST /discovery` is candidate generation only and does not choose final
matches, solve dependencies, or plan execution.
`GET /resolution/{slug}/{version}` returns direct authored dependencies only;
it does not expand transitive graphs or select versions for constraints.
The exact fetch routes intentionally separate immutable metadata from markdown
bytes so metadata reads stay JSON-oriented while raw content reads preserve
cache-friendly markdown delivery headers.
Publisher-supplied provenance may appear only on publish/exact metadata
responses as advisory data; discovery, resolution, and raw content routes remain
independent of Git, filesystem, or publisher-side state.
