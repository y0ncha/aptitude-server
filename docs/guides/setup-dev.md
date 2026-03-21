# Developer Setup

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

To validate Prometheus and Grafana locally with pinned Docker images:

```bash
make observability-up
```

This starts the API plus:

- Prometheus at `http://127.0.0.1:9090`
- Grafana at `http://127.0.0.1:3000`

The observability profile keeps migrations explicit by running the one-shot `migrate` service before the app starts. Shut the stack down with:

```bash
make observability-down
```
