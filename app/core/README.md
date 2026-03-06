# app.core module

Core domain logic and cross-layer contracts.

## Purpose

Defines business behavior for immutable skill registry operations and the ports
that infrastructure layers implement.

## Key Files

- `skill_registry.py`: immutable publish/fetch/list service + domain errors/models.
- `ports.py`: protocol contracts (`SkillRegistryPort`, `ArtifactStorePort`, `AuditPort`).
- `dependencies.py`: FastAPI dependency accessors for settings/services.
- `readiness.py`: readiness domain service and report models.
- `settings.py`: typed environment configuration.
- `logging.py`: centralized logging config for application and `uvicorn.*` loggers.

## Boundaries

- Core must not import persistence implementations directly.
- Persistence and audit adapters implement core-defined protocols.
- Logging configuration is defined once in core and reused by runtime entrypoints.
