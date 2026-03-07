# app.core module

Core domain logic and cross-layer contracts.

## Purpose

Defines business behavior for immutable skill catalog operations and the ports
that infrastructure layers implement.

## Key Files

- `skill_registry.py`: immutable publish/fetch/list service + domain errors/models.
- `ports.py`: protocol contracts (`SkillRegistryPort`, `ArtifactStorePort`, `AuditPort`).
- `dependencies.py`: FastAPI dependency providers and typed aliases
  (`SettingsDep`, `ReadinessServiceDep`, `SkillRegistryServiceDep`) that read
  process-scoped services from `request.app.state`.
- `readiness.py`: readiness domain service and report models.
- `settings.py`: typed environment configuration.
- `logging.py`: centralized logging config for application and `uvicorn.*` loggers.

## Boundaries

- Core must not import persistence implementations directly.
- Persistence and audit adapters implement core-defined protocols.
- Logging configuration is defined once in core and reused by runtime entrypoints.
- Dependency providers in `dependencies.py` assume startup has initialized
  `app.state.readiness_service` and `app.state.skill_registry_service`.
