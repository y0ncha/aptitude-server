# app.persistence module

Persistence adapters and storage infrastructure.

## Purpose

Implements core persistence ports for:

- PostgreSQL metadata persistence (SQLAlchemy)
- filesystem immutable artifact storage
- database lifecycle/readiness

## Key Files

- `db.py`: engine/session lifecycle and readiness probe adapter.
- `artifact_store.py`: filesystem artifact adapter.
- `skill_registry_repository.py`: SQLAlchemy skill catalog persistence adapter.
- `models/`: ORM models.

## Contracts

Adapters in this package implement protocols defined in `app.core.ports`.
