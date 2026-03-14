# Project Rules

## Approval Gates

- Any database schema change requires explicit user approval before implementation.
- Any public API contract change requires explicit user approval before implementation.

Schema changes include, for example:

- Alembic migrations
- SQLAlchemy model shape changes
- new or changed tables, columns, indexes, constraints, or relationships

API contract changes include, for example:

- request or response schema changes
- endpoint additions, removals, or path changes
- behavior changes that alter the documented external contract
- OpenAPI contract changes
