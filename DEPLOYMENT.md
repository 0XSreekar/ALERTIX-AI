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
- Run one or more `processing` replicas for the Redis event pipeline.
- Run ingestion through cron/GitHub Actions or the `ingestion` service.
- Keep ML weights mounted under `/models`; learned models refuse inference without checkpointed weights.

## Health Checks

- API: `/health`
- Processing metrics: `/api/processing/metrics`
- LLM internal health: `/internal/llm/health` with cron token where protected
