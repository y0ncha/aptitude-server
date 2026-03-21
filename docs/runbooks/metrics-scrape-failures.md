# Metrics and Scrape Failures

## Symptoms

- `/metrics` is unreachable
- Prometheus target is down
- Grafana panels show no data

## Checks

1. Probe `GET /metrics` directly from the app container or host.
2. Validate Prometheus config with `promtool check config`.
3. Confirm Prometheus can resolve `app:8000` inside the compose network.

## Actions

1. Restart the app container if `/metrics` is failing due to startup or readiness issues.
2. Fix broken scrape config, alert rules, or dashboard provisioning files.
3. Confirm the observability profile is running with `docker compose --profile observability ps`.
