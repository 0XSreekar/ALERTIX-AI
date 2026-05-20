# Alertix AI

India's open-source multi-hazard early-warning system. Live data from USGS, IMD, NASA FIRMS & more. Custom ML models + local LLM for alerts and citizen SOS triage. Covers earthquakes, floods, cyclones, wildfires & landslides. Zero paid APIs.

---

**Real-time multi-hazard disaster monitoring, prediction, and early-warning platform for India.**

Six hazard categories — earthquakes, floods, cyclones, wildfires, landslides, post-disaster damage — surfaced through a single live dashboard. Built on public data (USGS, IMD, NASA FIRMS, Google Flood Hub, CWC, Open-Meteo), open-source models, and a locally-hosted LLM for plain-language alert explanations and citizen SOS triage.

> Alertix AI provides hazard intelligence for situational awareness. It is **not** a substitute for official warnings from IMD, NCS, NDRF, or state authorities. Do not rely on Alertix AI for life-safety decisions.

## Status

Phase 1 (foundation, ingestion, APIs, dashboard) — complete. See [docs/runbook.md](docs/runbook.md) for the deployment checklist and [ALERTIX_AI_DOCUMENTATION.md](ALERTIX_AI_DOCUMENTATION.md) for the full project specification.

## Quick start (local dev)

Prerequisites: Docker Desktop, Node 20 LTS, Python 3.11, Git.

```bash
# 1. Copy env template and fill in values (see "Required external accounts" below)
cp .env.example .env

# 2. Bring up Postgres + Redis + backend + frontend
docker compose up --build

# 3. In another shell, run the first DB migration
docker compose exec backend alembic upgrade head

# 4. Trigger a USGS ingestion run
curl -X POST -H "X-Cron-Token: $CRON_TOKEN" http://localhost:8000/internal/ingest/usgs
```

Open `http://localhost:5173` for the dashboard and `http://localhost:8000/docs` for the API.

## Required external accounts (free tier)

| Service | Purpose | Notes |
|---|---|---|
| Supabase | Postgres + PostGIS + Auth | 500 MB DB, free |
| Upstash | Redis (cache + pub/sub) | 256 MB free |
| Cloudflare | R2 object storage + Pages (frontend) + Tunnel (LLM) | 10 GB R2 free |
| Render | Backend hosting | sleeps after 15 min idle |
| GitHub | Repo + Actions cron | unlimited public |
| Groq | LLM fallback (Phase 2) | Llama 3.1 70B free tier |
| Google AI Studio | LLM second fallback (Phase 2) | Gemini 1.5 Flash free tier |
| NASA FIRMS | Active fire data | free w/ MAP_KEY |
| Resend | Contact-form email | 100/day free |
| Sentry, Grafana Cloud | Monitoring | free tier |

See [docs/runbook.md](docs/runbook.md) for step-by-step provisioning.

## Repository structure

```
alertix-ai/
├── backend/        FastAPI + SQLAlchemy + Alembic + ingestion + ML
├── frontend/       React + Vite + Tailwind + shadcn/ui + Leaflet
├── ml/             Notebooks + training scripts (gitignored data/models)
├── .github/        CI/CD + cron workflows
└── docs/           architecture | api | data-sources | runbook | pitch
```

## Build phases

- **Phase 1** (complete) — backend infrastructure, DB, USGS + multi-source ingestion, all API endpoints, WebSocket, SOS form, full frontend, deployment, CI/CD, tests. **Exit criteria:** public URL shows live earthquakes within 5 min of USGS publication; login works.
- **Phase 2** — LLM integration (Ollama + Groq + Gemini fallback ladder, prompt templates, explanation/triage endpoints) and ML model training (seismic LSTM autoencoder, Omori, flood LSTM + U-Net, wildfire DBSCAN, landslide rules, damage DeepLabV3, composite XGBoost). **Exit criteria:** new seismic event triggers anomaly score + LLM explanation + WebSocket push to dashboard.

## License

See [LICENSE](LICENSE).
