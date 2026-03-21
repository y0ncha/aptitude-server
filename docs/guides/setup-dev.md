# Developer Setup

> This is the canonical local setup guide. The root `README.md` only keeps the
> condensed entrypoint and links back here for the full workflow.

This guide shows the simplest way to run `aptitude-server` locally for development.

## Prerequisites

- Python `3.12+`
- [`uv`](https://docs.astral.sh/uv/)
- Docker

## 1. Start PostgreSQL

From the repo root:

```bash
make db-up
```

This starts PostgreSQL on `127.0.0.1:5432` with:

- database: `aptitude`
- user: `postgres`
- password: `postgres`

## 2. Install Dependencies

```bash
uv venv
source .venv/bin/activate
uv sync --extra dev
```

## 3. Configure Environment

Set the required environment variables:

```bash
export DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/aptitude"
export AUTH_TOKENS_JSON='{"reader-token":["read"],"publisher-token":["read","publish"],"admin-token":["read","publish","admin"]}'
```

Optional:

```bash
export LOG_LEVEL="INFO"
export LOG_FORMAT="auto"
```

`LOG_FILE_PATH` is optional and only used by the Docker-based local observability profile.

## 4. Run Database Migrations

```bash
make migrate-up
```

## 5. Start The API

```bash
make run
```

Local URLs:

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Metrics: `http://127.0.0.1:8000/metrics`

## 6. Useful Commands

```bash
make test
make lint
make format
make typecheck
make migrate-down
make db-down
```

## Quick Check

Once the server is running:

```bash
curl http://127.0.0.1:8000/healthz
```

For authenticated routes, send one of the tokens from `AUTH_TOKENS_JSON` as:

```bash
Authorization: Bearer reader-token
```

Clients may also send an `X-Request-ID` header. The API echoes it on every response so you can correlate request logs, metrics, and audit rows.

## Optional Local Observability Profile

To validate metrics and logs locally with pinned Docker images:

```bash
make observability-up
```

This starts the API plus:

- Prometheus at `http://127.0.0.1:9090`
- Loki at `http://127.0.0.1:3100`
- OTLP gRPC at `http://127.0.0.1:4317`
- OTLP HTTP at `http://127.0.0.1:4318`
- Grafana at `http://127.0.0.1:3000`

Those services come from one `grafana/otel-lgtm` container. The observability profile keeps migrations explicit by running the one-shot `migrate` service before the app starts. Shut the stack down with:

```bash
make observability-down
```

### Verify Log Flow

Hit a simple route with a known request ID:

```bash
curl -H 'X-Request-ID: setup-dev-loki-check' http://127.0.0.1:8000/healthz
```

Then open Grafana and search for `setup-dev-loki-check` in the `Aptitude Server Logs` dashboard. That exercises the full local path from the API's JSON file sink through the embedded OpenTelemetry Collector into Loki.

### What Healthy Grafana Looks Like

- Grafana stays at `http://127.0.0.1:3000` in local development.
- Baseline HTTP panels should populate from `/healthz`, `/readyz`, and `/metrics` traffic.
- Route-specific registry panels stay empty until you exercise the matching publish, discovery, resolution, metadata, content, or lifecycle route.
- Use `X-Request-ID` when you want to correlate one request across Grafana logs, metrics-adjacent behavior, and audit rows.

### Exercise The Dashboard

Use the default local tokens from `AUTH_TOKENS_JSON` to populate both the baseline and route-specific panels:

```bash
SLUG="local.observability.$(date +%s)"
VERSION="1.0.0"

curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
curl http://127.0.0.1:8000/metrics

curl \
  -H 'Authorization: Bearer publisher-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "create_skill",
    "version": "1.0.0",
    "content": {"raw_markdown": "# Local Observability\n\nExercise the Grafana panels.\n"},
    "metadata": {
      "name": "Local Observability",
      "description": "Dashboard exercise skill",
      "tags": ["ops"],
      "headers": {"runtime": "python"},
      "inputs_schema": {"type": "object"},
      "outputs_schema": {"type": "object"},
      "token_estimate": 64,
      "maturity_score": 0.9,
      "security_score": 0.95
    },
    "governance": {"trust_tier": "untrusted", "provenance": null},
    "relationships": {
      "depends_on": [],
      "extends": [],
      "conflicts_with": [],
      "overlaps_with": []
    }
  }' \
  "http://127.0.0.1:8000/skills/${SLUG}/versions"

curl -H 'Authorization: Bearer reader-token' \
  "http://127.0.0.1:8000/skills/${SLUG}/versions/${VERSION}"
curl -H 'Authorization: Bearer reader-token' \
  "http://127.0.0.1:8000/skills/${SLUG}/versions/${VERSION}/content"
curl -H 'Authorization: Bearer reader-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Local Observability",
    "description": "Dashboard exercise skill",
    "tags": ["ops"]
  }' \
  http://127.0.0.1:8000/discovery
curl -H 'Authorization: Bearer reader-token' \
  "http://127.0.0.1:8000/resolution/${SLUG}/${VERSION}"
curl -X PATCH \
  -H 'Authorization: Bearer admin-token' \
  -H 'Content-Type: application/json' \
  -d '{"status":"deprecated","note":"Grafana dashboard exercise"}' \
  "http://127.0.0.1:8000/skills/${SLUG}/versions/${VERSION}/status"
```
