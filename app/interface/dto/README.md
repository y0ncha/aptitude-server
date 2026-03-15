# app.interface.dto module

Request and response DTOs for the public HTTP contract.

## Purpose

Defines Pydantic models and example payloads for publish, discovery,
resolution, exact immutable metadata fetch, and lifecycle-status APIs.

## Notes

- DTOs should mirror the public contract only; they should not preserve deleted
  route shapes.
- Publish body DTOs model only versioned content and metadata; the published
  skill `slug` is carried by the route path at `POST /skills/{slug}/versions`,
  and `intent` declares whether the caller is creating a new skill slug or
  publishing a version to an existing one.
- Raw markdown content fetch is modeled directly as an HTTP response, so this
  module keeps the immutable metadata envelope but not a markdown-body DTO.
