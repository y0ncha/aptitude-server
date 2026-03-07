# app.interface.api module

HTTP API routers for the service.

## Purpose

Defines FastAPI routes, request validation, response schemas, and API error
mapping for health and skill catalog operations.

## Key Files

- `health.py`: liveness/readiness endpoints (`/healthz`, `/readyz`).
- `skills.py`: publish/fetch/list immutable skill version endpoints.
- `__init__.py`: package marker.

## Notes

Business decisions should stay in core services; routers should focus on API
contract validation and error translation.
