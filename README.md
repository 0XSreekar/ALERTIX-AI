# Alertix AI

**Real-time multi-hazard disaster monitoring, prediction, and early-warning platform for India.**

Six hazard categories — earthquakes, floods, cyclones, wildfires, landslides, and post-disaster damage — ingested from live public sources, scored by purpose-built ML models, explained in plain language by an LLM, and surfaced through a unified operational dashboard.

> **Disclaimer:** Alertix AI provides hazard intelligence for situational awareness only. It is **not** a substitute for official warnings from IMD, NCS, NDRF, or state disaster management authorities. Do not rely on Alertix AI for life-safety decisions.

---

## What's inside

| Layer | What it does |
|---|---|
| **Ingestion** | 5 live data sources polled every 1–60 min via GitHub Actions cron |
| **ML models** | Seismic LSTM autoencoder + Omori aftershock, wildfire DBSCAN clustering, landslide IMD rainfall rules + GSI zones, flood GFH/CWC time-series, damage DeepLabV3 segmentation |
| **LLM** | Ollama (Qwen2.5-7B) → Groq (Llama 3.3-70B) → Gemini 1.5 Flash fallback ladder for alert explanations and SOS triage |
| **API** | FastAPI REST + WebSocket — events, alerts, predictions, SOS, damage, auth |
| **Dashboard** | React 18 + Leaflet live map, per-hazard tabs, real-time WebSocket feed, citizen SOS form |
| **Ops** | Docker Compose locally, Render (backend) + Cloudflare Pages (frontend) for zero-cost public demo |

---

## Hazard coverage

| Hazard | Data source | Model / logic |
|---|---|---|
| **Earthquake** | USGS GeoJSON feed (60s) + IRIS waveforms | LSTM autoencoder anomaly score + Omori-law aftershock probability |
| **Flood** | Google Flood Hub API (15min) + CWC river gauges (30min) | GFH/CWC intensity time-series with p10/p50/p90 bands; GFH agreement flag |
| **Cyclone** | IMD bulletins RSS (30min) | Latest track coordinates + impact zone |
| **Wildfire** | NASA FIRMS VIIRS/MODIS (60min) | DBSCAN hotspot clustering (50km radius, haversine) with risk classification |
| **Landslide** | Open-Meteo precipitation (live) + GSI zonation | IMD 24h rainfall thresholds per GSI zone across 15 Indian state regions |
| **Damage** | User image upload | Pretrained DeepLabV3 ResNet-50 (PASCAL VOC) — pixel-class breakdown + damage confidence |

---

## Quick start

**Prerequisites:** Docker Desktop, Node 20 LTS, Python 3.11, Git.

```bash
# 1. Clone and copy env template
git clone https://github.com/0XSreekar/ALERTIX-AI.git
cd ALERTIX-AI
cp .env.example .env          # fill in the values listed below

# 2. Start everything
docker compose up --build

# 3. Run DB migrations (first time only)
docker compose exec backend alembic upgrade head

# 4. Seed Indian regions (optional but recommended)
docker compose exec backend python scripts/seed_regions.py

# 5. Trigger a live data pull
curl -X POST -H "X-Cron-Token: your_cron_token" http://localhost:8000/internal/ingest/usgs
```

**Dashboard:** http://localhost:5173  
**API docs:** http://localhost:8000/docs

---

## Environment variables

Copy `.env.example` to `.env` and fill in:

```env
# Database (Supabase or local Postgres via Docker)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/alertix
DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@localhost:5432/alertix

# Redis (Upstash or local Redis via Docker)
REDIS_URL=redis://localhost:6379

# Auth — JWT secret (any random string for local dev)
SUPABASE_JWT_SECRET=change-me-in-production

# Internal cron protection
CRON_TOKEN=your-secret-cron-token

# Data sources
NASA_FIRMS_MAP_KEY=          # register at firms.modaps.eosdis.nasa.gov
GOOGLE_FLOOD_HUB_API_KEY=    # Google Cloud, Flood Hub API

# LLM (Phase 2)
OLLAMA_URL=http://localhost:11434          # local; expose via Cloudflare Tunnel for prod
OLLAMA_TUNNEL_URL=https://your-tunnel.trycloudflare.com
GROQ_API_KEY=                              # fallback — groq.com free tier
GEMINI_API_KEY=                            # second fallback — aistudio.google.com

# Object storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=alertix-media
R2_PUBLIC_URL=

# Email (contact form)
RESEND_API_KEY=
CONTACT_EMAIL=your@email.com

# Monitoring
SENTRY_DSN=
```

---

## Setting up Ollama (local LLM)

Alertix AI uses Qwen2.5-7B as the primary LLM for alert explanations and SOS triage.

```bash
# 1. Install Ollama
# Windows: https://ollama.com/download

# 2. Pull the model
ollama pull qwen2.5:7b

# 3. Verify GPU inference (RTX 3060 or better)
ollama run qwen2.5:7b "summarise a magnitude 5.2 earthquake near Delhi"

# 4. Expose your local Ollama for the Render backend via Cloudflare Tunnel
cloudflared tunnel --url http://localhost:11434
# copy the generated URL into OLLAMA_TUNNEL_URL in your .env
```

When your PC is offline, the backend auto-falls through to Groq (5s timeout), then Gemini, then a templated response marked `explanation_status = "degraded"`.

---

## Running without Docker (backend only)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# ML/inference deps (optional — needed for damage segmentation, DBSCAN)
pip install -e ".[ml]"

uvicorn app.main:app --reload --port 8000
alembic upgrade head
```

```bash
cd frontend
npm install
npm run dev        # Vite on :5173
```

---

## Repository structure

```
ALERTIX-AI/
├── backend/
│   ├── app/
│   │   ├── api/           REST endpoints (events, alerts, sos, predict, damage, auth, contact)
│   │   ├── ingestion/     USGS, NASA FIRMS, IMD, CWC, Google Flood Hub, Open-Meteo
│   │   ├── ml/            wildfire_cluster, landslide_rules, damage_segment,
│   │   │                  seismic_autoencoder, aftershock_omori, flood_lstm, flood_unet
│   │   ├── llm/           provider (Ollama→Groq→Gemini), ollama_client, groq_client, gemini_client
│   │   ├── models/        SQLAlchemy ORM: Event, Alert, SosReport, Profile, Region, AuditLog
│   │   ├── schemas/       Pydantic v2 schemas
│   │   ├── ws/            WebSocket: /ws/alerts, /ws/events
│   │   └── tasks/         APScheduler (local dev only)
│   ├── alembic/           DB migrations
│   ├── scripts/           seed_regions.py, backfill_usgs.py
│   └── tests/             test_auth, test_health, test_schemas, test_usgs_ingestion
│
├── frontend/
│   └── src/
│       ├── routes/
│       │   ├── Landing.tsx          Three.js earth + marketing
│       │   ├── Login.tsx / Signup.tsx
│       │   ├── About.tsx / Contact.tsx
│       │   └── Dashboard/
│       │       ├── index.tsx        Auth guard + tab layout
│       │       ├── EarthquakeTab    Live map + anomaly gauges + event table
│       │       ├── FloodTab         Basin risk cards (GFH/CWC) + event map
│       │       ├── CycloneTab       IMD bulletin feed + track map
│       │       ├── WildfireTab      FIRMS hotspot map + cluster stats
│       │       ├── LandslideTab     Rainfall threshold card + GSI zone + event map
│       │       ├── DamageTab        Image upload + DeepLabV3 results
│       │       ├── SosTab           Citizen distress form (DPDPA consent, GPS)
│       │       └── AlertsTab        Live alert feed via WebSocket
│       ├── components/    Map (Leaflet), AlertCard, RiskGauge, ThreeEarth, RegionSelector
│       └── lib/           api.ts, localAuth.ts, ws.ts, types.ts
│
├── ml/
│   └── scripts/           train_seismic_ae.py
│
├── .github/workflows/
│   ├── ci.yml             Lint + type-check + tests on every push
│   ├── deploy-backend.yml Render deploy on main push
│   ├── deploy-frontend.yml Cloudflare Pages deploy on main push
│   ├── cron-usgs.yml      USGS every 1 min (also wakes Render free tier)
│   ├── cron-firms.yml     NASA FIRMS every 60 min
│   ├── cron-imd.yml       IMD cyclone every 30 min
│   ├── cron-cwc.yml       CWC river gauges every 30 min
│   └── cron-google-flood-hub.yml  GFH every 15 min
│
└── docs/
    ├── architecture.md
    ├── api.md
    ├── data-sources.md
    ├── runbook.md
    └── pitch.md
```

---

## API reference (public endpoints)

All responses are JSON. Auth via `Authorization: Bearer <token>`.

```
GET  /api/events                    List events (filter: hazard_type, bbox, from/to)
GET  /api/events/recent             Last 24h events
GET  /api/events/{id}               Single event

GET  /api/alerts                    Active alerts
GET  /api/alerts/region?lat=&lon=&radius_km=   Alerts near a point
GET  /api/alerts/{id}               Alert + LLM explanation

POST /api/auth/signup               Register (email, password, full_name)
POST /api/auth/login                Login → JWT
GET  /api/auth/me                   Current user profile (requires token)

POST /api/sos                       Submit SOS report (DPDPA consent required)
GET  /api/sos/mine                  My reports (auth required)
GET  /api/sos/feed                  High-urgency feed (official/admin only)
DELETE /api/sos/mine/{id}           Right to deletion

GET  /api/predict/earthquake?lat=&lon=&radius_km=
GET  /api/predict/flood?basin_id=
GET  /api/predict/cyclone?storm_id=
GET  /api/predict/wildfire?bbox=
GET  /api/predict/landslide?lat=&lon=

POST /api/damage/segment            Upload image → DeepLabV3 segmentation (auth required)
POST /api/contact                   Contact form

WS   /ws/alerts                     Real-time alert stream (Redis pub/sub)
WS   /ws/events?hazard_type=        Real-time event stream

POST /internal/ingest/usgs          Cron-triggered (X-Cron-Token required)
POST /internal/ingest/firms
POST /internal/ingest/imd
POST /internal/ingest/cwc
POST /internal/ingest/google_flood_hub
POST /internal/llm/explain
POST /internal/llm/triage
GET  /internal/llm/health
```

---

## Deployment (zero-cost)

| Service | What runs there |
|---|---|
| **Cloudflare Pages** | React frontend — free, unlimited bandwidth, auto-deploys on push to `main` |
| **Render free tier** | FastAPI backend — sleeps after 15 min idle; USGS cron wakes it every minute |
| **Supabase free** | Postgres 15 + PostGIS — 500 MB, 2 CPU |
| **Upstash Redis** | Cache + pub/sub + streams — 256 MB free |
| **Cloudflare R2** | Waveforms + imagery — 10 GB free |
| **GitHub Actions** | CI/CD + 5 cron workflows — free for public repos |
| **Groq** | LLM fallback — llama-3.3-70b-versatile, free tier |
| **Google AI Studio** | LLM second fallback — Gemini 1.5 Flash, free tier |
| **Sentry + Grafana Cloud** | Error tracking + metrics — free tier |
| **Resend** | Contact form email — 100/day free |

See [docs/runbook.md](docs/runbook.md) for the full provisioning checklist.

---

## Tech stack

**Backend:** Python 3.11, FastAPI 0.115, SQLAlchemy 2 async, Alembic, Pydantic v2, asyncpg, APScheduler, SlowAPI, structlog, Sentry  
**Database:** PostgreSQL 15 + PostGIS (all geo columns SRID 4326)  
**Cache/queue:** Upstash Redis — Streams for ingestion, pub/sub for WebSocket fan-out  
**ML:** PyTorch, torchvision (DeepLabV3), scikit-learn (DBSCAN), ObsPy, shapely  
**LLM:** Ollama (Qwen2.5-7B-Instruct Q4_K_M) → Groq (llama-3.3-70b-versatile) → Gemini 1.5 Flash  
**Frontend:** TypeScript 5, React 18, Vite, Tailwind CSS, shadcn/ui, Leaflet + React-Leaflet, Recharts, Three.js, Framer Motion, TanStack Query, Zustand  
**Auth:** Local HS256 JWT (bcrypt passwords) — no Supabase Auth required  
**Storage:** Cloudflare R2 (boto3 S3-compatible)  
**CI/CD:** GitHub Actions — lint, typecheck, pytest, Render deploy, Cloudflare Pages deploy  

---

## Security

- JWT tokens expire after 72 hours; HS256 signed with `SUPABASE_JWT_SECRET`
- Internal cron endpoints require `X-Cron-Token` header
- Rate limiting: 60 req/min public · 5/hr anonymous SOS · 30/hr authenticated SOS
- IPs hashed in all logs — raw IPs never stored
- DPDPA 2023 consent checkbox required on SOS form
- Right to deletion: `DELETE /api/sos/mine/{id}`
- Every alert, SOS triage, and model inference writes to `audit_log`

---

## License

See [LICENSE](LICENSE).

Built by [0XSreekar](https://github.com/0XSreekar).
