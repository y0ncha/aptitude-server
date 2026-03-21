# app.observability module

Cross-cutting runtime observability and readiness helpers.

## Purpose

Groups logging, metrics, request-context propagation, and dependency readiness
under one package without mixing them into the skill-domain core.

## Key Files

- `context.py`: request-scoped metadata propagated through logs and audit
  events.
- `logging.py`: centralized process logging configuration, formatters, and the
  optional JSON file sink used by the local Loki stack.
- `metrics.py`: Prometheus-compatible counters, histograms, gauges, and
  exposition helpers.
- `readiness.py`: readiness service and report models built on core-defined
  readiness ports.

## Boundaries

- This package is runtime infrastructure, not business-domain logic.
- It may depend on `app.core` contracts such as ports and audit-event helpers.
- HTTP route definitions stay in `app.interface.api`; this package only exposes
  reusable runtime helpers those routes call.
- The optional file sink is for local observability only; production log
  backends remain external deployment choices.
- The structured file sink is intentionally scoped to application logs; noisy
  access logs stay on stdout so Grafana can show one compact request-oriented
  line per application event instead of duplicated access noise.
