# app.audit module

Audit infrastructure adapters.

## Purpose

Implements core audit contracts and persists domain audit events durably.

## Key Files

- `recorder.py`: `SQLAlchemyAuditRecorder`, concrete implementation of `AuditPort`.
- `__init__.py`: package marker.

## Contracts

- Implements `app.core.ports.AuditPort`.
- Writes to `AuditEvent` ORM model via SQLAlchemy sessions.

## Notes

This package currently handles standalone audit writes for read activity and
denied governance actions. Successful publish and lifecycle mutation audits are
written transactionally by the persistence adapter in the same database commit
as the authoritative state change.
