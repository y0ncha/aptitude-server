# app.persistence module

Persistence adapters and storage infrastructure.

## Purpose

Implements core persistence ports for:

- PostgreSQL metadata persistence (SQLAlchemy)
- digest-addressed immutable markdown storage in PostgreSQL
- authored relationship selector preservation for exact dependency reads
- exact immutable metadata and content lookup for one `slug@version`
- advisory search read model and indexed candidate retrieval
- database lifecycle/readiness

## Key Files

- `db.py`: engine/session lifecycle and readiness probe adapter.
- `skill_registry_repository.py`: composed SQLAlchemy adapter that exposes the
  existing repository class name while delegating behavior to port-aligned
  mixins.
- `skill_registry_repository_base.py`: shared session and helper logic for the
  repository mixins.
- `skill_registry_repository_writes.py`: publish/write-side repository methods.
- `skill_registry_repository_reads.py`: exact version/content/relationship read methods.
- `skill_registry_repository_search.py`: advisory search candidate retrieval.
- `skill_registry_repository_status.py`: lifecycle-status update methods.
- `skill_registry_repository_support.py`: shared projections, query helpers, and
  search SQL.
- `models/`: ORM models.

## Contracts

Adapters in this package implement protocols defined in `app.core.ports`.
The repository owns atomic publish/status writes, including audit rows that must
commit in the same transaction as authoritative lifecycle changes.
Canonical short summary text lives on `skill_metadata.description`; deduplicated
`skill_contents` rows persist only markdown plus checksum and size metadata.
