# Alertix AI — Deployment Runbook

## Prerequisites

- Docker Desktop installed
- Node 20 LTS
- Python 3.11
- Git
- Accounts created (all free tier): Supabase, Upstash, Cloudflare, Render, GitHub, Sentry, Resend

## Step 1: Provision Supabase

1. Go to [supabase.com](https://supabase.com), create a new project.
2. In **Settings > Database**, note the connection string (replace `[YOUR-PASSWORD]`).
3. In **Settings > API**, copy:
   - `SUPABASE_URL` (project URL)
   - `SUPABASE_ANON_KEY` (anon public)
   - `SUPABASE_SERVICE_ROLE_KEY` (service_role)
4. In **Settings > Auth > JWT Settings**, copy the JWT Secret.
5. Enable the PostGIS extension: go to **Database > Extensions**, search "postgis", enable it.

## Step 2: Provision Upstash Redis

1. Go to [upstash.com](https://upstash.com), create a Redis database.
2. Copy the `REDIS_URL` (use the `redis://` format, not REST).

## Step 3: Provision Cloudflare

1. Create a Cloudflare account if you don't have one.
2. **R2**: Create a bucket named `alertix`. Note your Account ID, Access Key, Secret.
3. **Pages**: Will be set up via GitHub Actions (deploy-frontend.yml). Create an API token with Pages edit permission.
4. **Tunnel** (Phase 2): Install cloudflared, create a named tunnel for Ollama.

## Step 4: Create .env

```bash
cp .env.example .env
# Fill in all values from Steps 1-3
```

## Step 5: Local dev

```bash
docker compose up --build
# In another terminal:
docker compose exec backend alembic upgrade head
# Test USGS ingestion:
curl -X POST -H "X-Cron-Token: YOUR_TOKEN" http://localhost:8000/internal/ingest/usgs
# Open http://localhost:5173
```

## Step 6: Deploy backend to Render

1. Go to [render.com](https://render.com), create a new **Web Service**.
2. Connect your GitHub repo, select the `backend/` directory.
3. Settings:
   - **Build command**: `pip install -e .`
   - **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: Free
4. Add all backend env vars from `.env` to Render's Environment tab.
5. Note the public URL (e.g., `https://alertix-backend.onrender.com`).
6. Copy the Deploy Hook URL for CI/CD.

## Step 7: Deploy frontend to Cloudflare Pages

1. The `deploy-frontend.yml` workflow handles this automatically on push to main.
2. Add these GitHub Secrets:
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
   - `VITE_API_BASE_URL` (Render backend URL)
   - `VITE_WS_BASE_URL` (same, but `wss://`)
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`

## Step 8: Configure GitHub Actions cron

Add these GitHub Secrets:
- `BACKEND_URL` — your Render public URL (no trailing slash)
- `CRON_TOKEN` — must match the `CRON_TOKEN` env var on Render

The cron workflows will start running automatically:
- USGS: every 5 minutes
- FIRMS: every hour at :15
- IMD: every 30 minutes
- CWC: every 30 minutes
- Flood ingestion: every 30 minutes via CWC and configured official bulletin URLs

## Step 9: Verify

1. Wait 5 minutes for the first USGS cron to fire.
2. Open the frontend URL.
3. Sign up, log in, navigate to Dashboard > Earthquake.
4. Live earthquakes should appear on the map.

## Step 10: Monitoring (optional but recommended)

- **Sentry**: Add `SENTRY_DSN_BACKEND` to Render env vars. Add `VITE_SENTRY_DSN` to Cloudflare Pages env vars.
- **Grafana Cloud**: Set up a free account, configure Prometheus endpoint on the backend (add in Phase 2).

## Model weights, AI guardrails and metrics

- Provision model checkpoints (S3/R2) into the backend `models/` directory or configure an object-storage sync. The backend reads `model_weights_dir` from settings and will load checkpoints when present. Set `require_model_weights=true` in `.env` to fail fast if checkpoints are missing.
- AI guardrails are enabled by default (`enable_ai_guardrails=true`). To change behavior, toggle this env var. Guardrails block requests that ask for exact predictions or official evacuation orders.
- Ingestion metrics are exposed at `GET /api/ingest/metrics` and a health snapshot at `GET /api/ingest/health`. Processing metrics remain at `GET /api/processing/metrics`.


## Troubleshooting

| Issue | Fix |
|---|---|
| Render sleeping mid-request | The USGS cron wakes it every 5 min. First request after sleep takes 30-60s. |
| Supabase DB full (500 MB) | Archive events older than 90 days to R2 as Parquet. |
| USGS endpoint returns 503 | USGS may rate-limit. The cron retries next cycle. |
| Frontend shows "API error" | Check CORS: ensure `CORS_ORIGINS` includes your Cloudflare Pages domain. |
| WebSocket not connecting | Use `wss://` in production. Check Render supports WebSocket (it does on paid; free may timeout). |
