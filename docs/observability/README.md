# Alertix Observability

## Endpoints

- `GET /api/ingest/metrics` — Prometheus text format, per-source ingestion counters
- `GET /api/processing/metrics` — Prometheus text format, processing worker counters
- `GET /api/health` — overall liveness

## Grafana Cloud setup

1. Create a free Grafana Cloud stack (https://grafana.com/products/cloud/).
2. Add a Prometheus data source pointing at your scrape endpoint (Grafana Agent or
   Hosted Prometheus). For local dev, the docker-compose `prometheus` service
   already scrapes `backend:8000/api/ingest/metrics` and `/api/processing/metrics`.
3. Dashboards → New → Import → upload `grafana-dashboard.json`.
4. Pick the Prometheus data source when prompted.

## Metric reference

| Metric | Labels | Meaning |
|---|---|---|
| `alertix_ingest_fetched_total` | `source` | Records pulled from upstream |
| `alertix_ingest_parsed_total` | `source` | Successfully parsed |
| `alertix_ingest_valid_total` | `source` | Passed validation |
| `alertix_ingest_malformed_total` | `source` | Failed validation |
| `alertix_ingest_duplicates_total` | `source` | Skipped because `(source, external_id)` already exists |
| `alertix_ingest_stored_total` | `source` | Upserted into `events` |
| `alertix_ingest_streamed_total` | `source` | Published to Redis Stream |

The dashboard panel queries assume Prometheus, 6h time window, 30s refresh.
