# ALERTIX Deployment

## Local Production-Like Stack

1. Copy `.env.example` to `.env` and fill required secrets.
2. Start the stack:

```bash
docker compose up --build
```

3. Apply migrations from the backend container:

```bash
docker compose exec backend alembic upgrade head
```

Services:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Nginx reverse proxy: `http://localhost:8080`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Production Notes

- Store all secrets in the host secret manager or deployment platform, never in git.
- Keep `SUPABASE_JWT_SECRET`, database URLs, Redis URL, R2 keys, and LLM provider keys out of images.
- Set `APP_ENV=production` and `ENVIRONMENT=production`; the backend will reject weak JWT and cron secrets outside development.
- Use the Supabase/managed Postgres pooler for deployed services. Start with `DB_MAX_CONNECTIONS=10` and `DB_POOL_MIN_SIZE=2` per service, then increase only after checking provider limits.
- Run one or more `processing` replicas for the Redis event pipeline.
- Processing uses a Redis Stream consumer group (`REDIS_STREAM_GROUP=alertix-processing`) so crashed workers can recover pending entries.
- Run ingestion through cron/GitHub Actions or the `ingestion` service. Keep `REDIS_STREAM_MAXLEN` high enough for outage recovery.
- Keep ML weights mounted under `/models`; learned models refuse inference without checkpointed weights.
- Use `STORAGE_BACKEND=r2` in production; local uploads are only suitable for development.
- Migration `008` removes redundant indexes and creates BRIN indexes plus `retention_policies`. Schedule archive/delete jobs from those policies before high-volume ingestion.

## Database Readiness

Before opening the system to realtime traffic:

```bash
cd backend
alembic upgrade head
python inspect_db.py
```

Check that Alembic reports `008` or newer, duplicate location/time indexes are gone, and `retention_policies` exists.

Large production installs should eventually migrate append-heavy tables to range partitioning by timestamp:

- `hazard_events.event_timestamp`
- `events.occurred_at`
- `earthquakes.occurred_at`
- `river_gauges.observed_at`
- `weather_events.observed_at`
- `wildfires.detected_at`
- `audit_log.created_at`

Do that as a planned maintenance migration after deciding the hot-data window; converting existing populated tables to partitions is intentionally not done automatically.

## Health Checks

- API: `/health`
- Processing metrics: `/api/processing/metrics`
- LLM internal health: `/internal/llm/health` with cron token where protected
