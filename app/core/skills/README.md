# app.core.skills module

Skill-domain services, models, and projections within the core layer.

## Purpose

Groups the immutable skill-catalog bounded context under one package without
changing the top-level server layering.

## Key Files

- `registry.py`: immutable publish and lifecycle-status service plus related
  domain exports.
- `discovery.py`: discovery facade for ordered candidate slug retrieval.
- `fetch.py`: exact immutable metadata and markdown fetch service.
- `resolution.py`: exact direct dependency read service for authored
  `depends_on` selectors.
- `search.py`: advisory search query/result models and implementation reused by
  discovery.
- `models.py`: skill-domain commands, result models, and domain errors.
- `projections.py`: stored-to-domain projections for immutable version details.
- `exact_read.py`: shared exact-read policy and audit orchestration reused by
  fetch and resolution.

## Boundaries

- This package remains part of the `app.core` layer, not a separate
  architectural tier.
- Modules in this package may depend on other `app.core` cross-cutting modules,
  but must not import persistence adapters directly.
- Keep package-local imports relative when the dependency stays inside the
  skill-domain cluster.
