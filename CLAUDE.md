# Alertix AI — Claude Code Project Guide

## What is this project?

Real-time multi-hazard disaster monitoring, prediction, and early-warning platform for India.
Covers earthquakes, floods, cyclones, wildfires, landslides, and post-disaster damage assessment.
Full specification lives in `ALERTIX_AI_DOCUMENTATION.md` at the repo root — that is the single source of truth.

## Repository layout

```
backend/          Python 3.11 FastAPI backend (SQLAlchemy 2 async, Alembic, Pydantic v2)
frontend/         TypeScript React 18 + Vite + Tailwind + shadcn/ui
ml/               Jupyter notebooks + training scripts (data/ and models/ are gitignored)
.github/          CI/CD + cron workflows (GitHub Actions)
docs/             Architecture, API, data-sources, runbook, pitch
```

## Build & run commands

### Backend (from `backend/`)
```bash
# Install deps (use a venv)
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run migrations
alembic upgrade head

# Lint + format
ruff check . --fix && ruff format .

# Type check
mypy app/

# Tests
pytest
pytest --cov=app
```

### Frontend (from `frontend/`)
```bash
npm install
npm run dev          # Vite dev server on :5173
npm run build        # Production build
npm run lint         # ESLint
npm run typecheck    # tsc --noEmit
npm run test         # Vitest
```

### Full stack (from repo root)
```bash
docker compose up --build   # Postgres + Redis + backend + frontend
```

## Tech stack (locked — do not substitute)

- **Backend:** Python 3.11, FastAPI 0.115+, SQLAlchemy 2.x async, Alembic, Pydantic v2, APScheduler
- **Frontend:** TypeScript 5, React 18 + Vite, Tailwind CSS + shadcn/ui, Leaflet + React-Leaflet, Recharts, Framer Motion, Three.js (landing only), TanStack Query + Zustand
- **Database:** Supabase Postgres 15 + PostGIS (all geo columns use SRID 4326)
- **Cache/queue:** Upstash Redis (Streams for ingestion, pub/sub for WebSocket fan-out)
- **Auth:** Local FastAPI auth in `app/api/auth.py` (bcrypt + HS256 JWT issued via `/api/auth/signup` and `/api/auth/login`). Three roles: citizen, official, admin. Frontend stores the token via `src/lib/localAuth.ts` in `localStorage`; `src/lib/api.ts` forwards it as `Authorization: Bearer <token>`. The HS256 secret is read from `SUPABASE_JWT_SECRET` (name kept for legacy; falls back to a dev default if unset).
- **LLM model on Groq:** `llama-3.3-70b-versatile` (Llama 3.1 was decommissioned).
- **Object storage:** Cloudflare R2
- **LLM (Phase 2 only):** Ollama Qwen2.5-7B → Groq Llama 3.1 70B → Gemini 1.5 Flash fallback ladder
- **Hosting:** Backend on Render free, frontend on Cloudflare Pages, cron via GitHub Actions

## Key conventions

- All timestamps are UTC. All geography columns use SRID 4326.
- Internal endpoints live under `/internal/` and require `X-Cron-Token` header.
- Public API endpoints start with `/api/`. WebSocket endpoints start with `/ws/`.
- Upsert ingestion data by `(source, external_id)` — reruns must be idempotent.
- Never store raw IPs — hash on logging.
- Every alert and SOS triage writes to `audit_log`.
- Rate limiting: 60 req/min public, 5/hr anonymous SOS, 30/hr authenticated SOS.
- Footer disclaimer required on every frontend page (see Section 14.6 of the spec).

## Two-phase build

- **Phase 1:** All infrastructure, DB, ingestion, APIs, WebSocket, SOS form, frontend, deployment, CI/CD, tests. NO LLM or ML model training.
- **Phase 2:** LLM integration (Ollama/Groq/Gemini), ML model training (seismic LSTM, Omori, flood LSTM, U-Net, wildfire DBSCAN, landslide rules, damage DeepLabV3, composite XGBoost).

## Environment

`.env.example` documents every variable. Copy to `.env` and fill in. Never commit `.env`.
Frontend env vars must be prefixed with `VITE_`.

## External data sources

USGS (earthquakes), IRIS (waveforms), IMD/RSMC + JTWC (cyclones), NASA FIRMS (wildfires), CWC India (river gauges), official flood bulletins, Open-Meteo (weather/rainfall), GSI (landslide zones), Sentinel-1 (SAR for flood extent). All free for non-commercial use.
