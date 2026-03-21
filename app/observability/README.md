# app.observability module

Cross-cutting runtime observability and readiness helpers.

## Purpose

Groups logging, metrics, request-context propagation, and dependency readiness
under one package without mixing them into the skill-domain core.

## Key Files

- `context.py`: request-scoped metadata propagated through logs and audit
  events.
- `logging.py`: centralized process logging configuration and formatters.
- `metrics.py`: Prometheus-compatible counters, histograms, gauges, and
  exposition helpers.
- `readiness.py`: readiness service and report models built on core-defined
  readiness ports.

## Boundaries

- This package is runtime infrastructure, not business-domain logic.
- It may depend on `app.core` contracts such as ports and audit-event helpers.
- HTTP route definitions stay in `app.interface.api`; this package only exposes
  reusable runtime helpers those routes call.
