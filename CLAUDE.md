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
- **Object storage:** Cloudflare R2
- **LLM provider ladder (Phase 2):** Ollama (local, optional) → **Cerebras (primary cloud)** → Groq → Gemini → templated fallback. Wiring lives in `backend/app/llm/provider.py`. API keys go in `.env` (`CEREBRAS_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`).
- **Primary LLM:** Cerebras Inference, model `llama3.1-8b` (set via `CEREBRAS_MODEL` in `.env`). The Llama-3.3-70B in the original spec is not on Cerebras's current free tier; the 235B Qwen MoE is available but rate-limits aggressively under the worker's 30s tick. Llama3.1-8b fits the 30 req/min quota cleanly.
- **Groq fallback model:** `llama-3.3-70b-versatile` (Llama 3.1 was decommissioned).
- **Local LLM (optional, privacy/offline path):** Ollama Qwen2.5-7B. Provider checks Ollama health first and skips it silently if not running, so leaving Ollama off is fine in dev.
- **Hosting:** Backend on Render free, frontend on Cloudflare Pages, cron via GitHub Actions

## Workflow

- **After finishing any non-trivial change, commit and push to GitHub.** The
  remote is `origin` → `https://github.com/0XSreekar/ALERTIX-AI.git`. Standard
  flow: `git add` only the files you touched, write a conventional commit
  message, `git push origin <branch>`. Do not skip hooks. Do not force-push to
  `main`. Open a PR for cross-cutting changes; small fixes can go directly to
  the working branch.

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
- **Phase 2:** LLM integration (Cerebras primary; Ollama/Groq/Gemini fallbacks) and ML model training (seismic LSTM autoencoder, Omori aftershocks, flood LSTM, U-Net flood extent, wildfire DBSCAN, landslide rules, damage DeepLabV3, composite XGBoost risk index). Training scripts live in `ml/scripts/`; weights are referenced via `.env` (`SEISMIC_AE_CHECKPOINT`, `FLOOD_LSTM_CHECKPOINT`, `DAMAGE_MODEL_CHECKPOINT`, `RISK_INDEX_CHECKPOINT`). Inference modules in `backend/app/ml/` degrade gracefully when weights are missing.

## Environment

`.env.example` documents every variable. Copy to `.env` and fill in. Never commit `.env`.
Frontend env vars must be prefixed with `VITE_`.

## Phase 3 — Sentinel "Live Threat Theatre"

Single flagship feature replacing the feel of "another dashboard tab." Lives at
`/dashboard/sentinel`. Active development; not all components are complete.

**Components (each gated by a feature flag; build them in this order):**

| # | Component | Backend | Frontend | Status |
|---|---|---|---|---|
| 1 | 3D India globe (Three.js / R3F) | — | `routes/Dashboard/SentinelTab.tsx`, `components/sentinel/Globe.tsx` | building |
| 2 | Live event particles over WS | reuses `/ws/events` | particle system inside Globe | building |
| 3 | Top-threats sidebar | `GET /api/sentinel/threats` | `components/sentinel/ThreatList.tsx` | building |
| 4 | Time slider (-7d → +72h) | reuses `/api/events` with `from`/`to` | `components/sentinel/TimeSlider.tsx` | building |
| 5 | Forecast cones (cyclone, flood, seismic) | reuses `/api/predict/*` | overlay layer in Globe | pending |
| 6 | WorldPop population-at-risk | `GET /api/sentinel/impact?event_id=` | drill-down panel | pending |
| 7 | AI Briefing Bar (Gemini RAG, grounded only on visible events) | `POST /api/sentinel/brief` | `components/sentinel/BriefingBar.tsx` | building |
| 8 | Cascading hazard graph (force-directed) | `GET /api/sentinel/cascades` | `components/sentinel/CascadeGraph.tsx` | pending |
| 9 | Drill-down SitRep panel (Gemini-generated, citation-linked) | `POST /api/sentinel/sitrep` | `components/sentinel/SitRepPanel.tsx` | pending |

**Accuracy constraint:** every particle, cone, and number on this surface MUST trace
to a real DB row or a model we've trained. No demo bezels, no fabricated populations.
The AI briefing prompt always passes the on-screen event payload as context — Gemini
must cite event IDs in its response; ungrounded answers are rejected by the frontend.

## External data sources

USGS (earthquakes), IRIS (waveforms), IMD/RSMC + JTWC (cyclones), NASA FIRMS (wildfires), CWC India (river gauges), official flood bulletins, Open-Meteo (weather/rainfall), GSI (landslide zones), Sentinel-1 (SAR for flood extent). All free for non-commercial use.
