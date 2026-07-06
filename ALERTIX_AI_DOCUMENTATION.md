# ALERTIX AI — Complete Project Documentation

**Real-Time Multi-Hazard Disaster Monitoring, Prediction, and Early-Warning Platform**

| Field | Value |
|---|---|
| Version | 1.0 |
| Build type | Solo, 1 month |
| Budget | Zero rupees |
| Hardware | RTX 3060-class GPU, 16 GB RAM |
| Geographic focus | India (CWC + IMD + USGS + NASA FIRMS) |
| Primary LLM | Qwen2.5-7B-Instruct (local) + Groq API (fallback) |
| Author | Project owner |
| Document purpose | Single source of truth for build, pitch, and handover |

---

## Table of Contents

1. Executive Summary
2. Honest Scope Statement
3. System Architecture
4. Technology Stack (Locked)
5. Data Sources
6. AI / ML Models
7. Local LLM Strategy
8. Database Schema
9. API Surface
10. Frontend Specification
11. Deployment Architecture (Zero-Cost)
12. Phase-Wise Build Plan
    - Phase 0 — Pre-Flight
    - Phase 1 — Foundation (Week 1)
    - Phase 2 — Core AI Layer (Week 2)
    - Phase 3 — Multi-Hazard Expansion (Week 3)
    - Phase 4 — Polish and Production (Week 4)
    - Phase 5 — Post-Launch Roadmap
13. Repository Structure
14. Security and Privacy
15. Pitfalls and Failure Modes
16. Pitch Positioning
17. Earthquake Prediction — Technical Honesty Note
18. Glossary

---

## 1. Executive Summary

Alertix AI is a real-time multi-hazard monitoring, prediction, and early-warning platform built for the Indian context. It combines live data ingestion from public sources (USGS, IRIS, IMD/RSMC, JTWC, NASA FIRMS, CWC, Open-Meteo), classical and deep learning models, and a locally-hosted Large Language Model that produces plain-language alert explanations and triages citizen Save-Our-Souls (SOS) reports.

The platform is built by a single developer in four weeks on consumer hardware (RTX 3060, 16 GB RAM) using exclusively free-tier services. It covers six hazard categories: **earthquakes, floods, cyclones, wildfires, landslides, and post-disaster damage assessment**. Two of those hazards (earthquakes and floods) have proprietary AI models trained as part of the build; the remaining four are powered by reliable public live-data feeds and surfaced through a unified operational dashboard.

The headline differentiator versus incumbents (Google Flood Hub, IBM Environmental Intelligence, Microsoft AI for Earth, NVIDIA Earth-2) is the combination of (a) on-premise / open-source deployability, (b) multilingual citizen-report triage using a local LLM, (c) anomaly-driven alerting that does not pretend to be ground-truth prediction, and (d) cost structure that allows pilots with state disaster management authorities and insurers who cannot afford watsonx-class subscriptions.

---

## 2. Honest Scope Statement

This section exists because over-claiming kills disaster-tech startups when the first real event hits and the system underperforms its marketing.

### 2.1 What Alertix AI does

- Ingests real-time hazard data from 6+ public sources every 1–5 minutes.
- Stores every event with full provenance (source, timestamp, model version) in PostGIS.
- Runs proprietary models for seismic anomaly detection and flood discharge forecasting.
- Surfaces all hazards on a unified live map with severity, probability, and explanation layers.
- Generates LLM-written alert explanations in English and (where the model supports it) Hindi.
- Accepts citizen SOS submissions, extracts location via NER + geocoding, scores urgency.
- Provides damage-assessment image upload with pretrained segmentation.
- Issues alerts via the dashboard (and, optionally, email) within 90 seconds of source publish.

### 2.2 What Alertix AI does not do in v1

- Does not bypass or replace national early-warning systems (IMD, NCS, NDRF).
- Does not provide tactical evacuation routing in production (routing demo is illustrative).
- Does not perform automated cross-agency coordination (requires contracts, not code).
- Does not filter misinformation at scale (research-grade open problem).
- Does not guarantee uptime suitable for life-safety reliance (state this on every page).

### 2.3 Models that are real vs. surface-data integrations

| Hazard | Status | What runs underneath |
|---|---|---|
| Earthquake | Real AI (proprietary) | LSTM autoencoder on USGS waveform features; aftershock probability via Omori law fit; LLM characterization |
| Flood | Real AI (proprietary + partner data) | LSTM discharge forecast on CWC + Open-Meteo; U-Net flood extent on Sentinel-1; official bulletin validation as additional input |
| Cyclone | Live data integration | IMD cyclone bulletins; ECMWF / Open-Meteo wind fields; no proprietary model in v1 |
| Wildfire | Live data integration | NASA FIRMS VIIRS/MODIS active fire detections; no proprietary prediction in v1 |
| Landslide | Static + rule-based | GSI India landslide hazard zonation overlay; rainfall threshold rules from published literature |
| Damage assessment | Pretrained model | Segment Anything / U-Net on uploaded imagery; no fine-tuning in v1 |

This table is the source of truth. Update it as components ship.

---

## 3. System Architecture

### 3.1 High-level diagram

```
┌─────────────── DATA INGESTION LAYER ─────────────────────┐
│  USGS earthquake feed          (every 60 s)              │
│  IRIS FDSN waveforms           (on-demand via ObsPy)     │
│  CWC India river gauges        (every 30 min, HTML)      │
│  Official flood bulletins      (configured URLs)         │
│  IMD/RSMC + JTWC cyclone       (every 30 min, HTML/text) │
│  NASA FIRMS active fires       (every 60 min)            │
│  Open-Meteo weather            (on-demand per region)    │
│  User SOS form                 (event-driven)            │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────── MESSAGE QUEUE (Redis Streams) ───────────────┐
│  Decouples ingestion from processing                     │
└──────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────── PROCESSING LAYER ─────────────────────┐
│  Earthquake: LSTM autoencoder anomaly + Omori aftershock │
│  Flood:      LSTM discharge + U-Net extent + bulletins   │
│  Cyclone:    Track extrapolation + impact estimation     │
│  Wildfire:   FIRMS clustering + risk classification      │
│  Landslide:  Rainfall threshold rules + GSI overlay      │
│  Text:       Qwen2.5-7B triage + spaCy geolocation       │
│  Damage:     Pretrained segmentation on uploads          │
└──────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────── STORAGE LAYER ────────────────────────┐
│  Postgres + PostGIS  (events, alerts, users)             │
│  Cloudflare R2       (waveforms, imagery)                │
│  Upstash Redis       (cache, hot alerts, queue)          │
└──────────────────────────────────────────────────────────┘
                            ↓
┌─────────────── API LAYER (FastAPI) ──────────────────────┐
│  REST + WebSocket + Server-Sent Events                   │
│  Local FastAPI auth — bcrypt + HS256 JWT in HttpOnly     │
│  cookie; short-lived ticket for WebSocket upgrades       │
└──────────────────────────────────────────────────────────┘
                            ↓
┌─────────── FRONTEND (React + Vite + TS) ─────────────────┐
│  Landing / About / Contact / Auth                        │
│  Dashboard: Leaflet + Recharts + live WebSocket feed     │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Data flow per hazard event

1. Ingestion worker pulls source → normalizes to common Event schema.
2. Event is written to Postgres with PostGIS geometry.
3. Event is pushed to Redis stream `hazard:events`.
4. Processing worker consumes from stream, runs hazard-specific model, writes back to Postgres with `anomaly_score`, `probability`, etc.
5. If severity crosses threshold, processing worker creates an `Alert` row and publishes to Redis pub/sub channel `alerts:new`.
6. WebSocket server subscribes to `alerts:new`, fans out to connected dashboards.
7. LLM worker (separate, async) picks up new alerts and writes the `explanation` field once Qwen produces text.
8. Dashboard updates in real time; offline clients catch up via REST poll on reconnect.

### 3.3 Why this architecture and not simpler

- A simpler design (single FastAPI process, no Redis, polling instead of WebSocket) works for the demo but does not survive even one production pilot. The current design is the smallest design that does survive.
- Redis is the cheapest unit of "messaging" you can add. Skipping it forces you to do everything in-process, which means a slow LLM call blocks ingestion. That is unacceptable.
- PostGIS is non-negotiable: every hazard query is spatial.

---

## 4. Technology Stack (Locked)

Every line is the final choice. No menu, no alternatives in the build doc — alternatives belong in design discussions, not implementation.

| Layer | Choice |
|---|---|
| Backend language | Python 3.11 |
| Backend framework | FastAPI 0.115+ |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Background jobs | APScheduler (v1), Celery (v2) |
| Frontend language | TypeScript 5.x |
| Frontend framework | React 18 + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| Mapping | Leaflet + React-Leaflet + OpenStreetMap tiles |
| Charts | Recharts |
| Animations | Framer Motion, Three.js (landing only) |
| State management | TanStack Query + Zustand |
| Primary database | Supabase Postgres 15 + PostGIS |
| Time-series option | TimescaleDB extension (Phase 5 only) |
| Cache + queue | Upstash Redis (free tier) |
| Object storage | Cloudflare R2 (10 GB free) |
| Auth | Supabase Auth |
| ML framework | PyTorch 2.x |
| Classical ML | scikit-learn, XGBoost, CatBoost |
| NLP toolkit | spaCy + transformers |
| Seismic library | ObsPy |
| Geospatial libs | GeoPandas, Shapely, Rasterio, Folium (for prototypes) |
| Local LLM runtime | Ollama (dev), llama.cpp (server) |
| Primary LLM | Qwen2.5-7B-Instruct Q4_K_M |
| Fallback LLM | Groq API (Llama 3.1 70B, free tier) |
| Geocoding | Self-hosted Nominatim (Docker) + GeoNames India dump |
| Backend hosting | Render free web service |
| Frontend hosting | Cloudflare Pages (unlimited bandwidth, free) |
| LLM bridge | Cloudflare Tunnel (free) |
| Cron triggers | GitHub Actions scheduled workflows |
| CI/CD | GitHub Actions |
| Monitoring | Grafana Cloud free + Sentry free |
| Email | Resend (100/day free) |
| Containerization | Docker + docker-compose |
| Testing (backend) | pytest + pytest-asyncio |
| Testing (frontend) | Vitest + React Testing Library |
| End-to-end testing | Playwright |
| Code formatting | Ruff (Python), Prettier (TS) |
| Type checking | mypy (Python), tsc (TS) |

---

## 5. Data Sources

Every source is free for non-commercial use. Commercial licensing must be revisited before paid pilots.

### 5.1 Earthquakes
- **USGS Earthquake Hazards Program** — GeoJSON feeds (`all_hour`, `all_day`, `significant_week`). No key, no rate limit beyond fair use.
- **IRIS FDSN web services** — raw waveforms via ObsPy. Used for autoencoder training and historical analysis. Fair use only.

### 5.2 Floods
- **CWC (Central Water Commission)** — river gauge readings. Public website; respect robots and rate. Obtain MoU before commercial deployment.
- **Official state flood bulletins** — optional configured sources; only geotagged, validated bulletins are stored.
- **Open-Meteo** — precipitation forecasts, no key, no rate limit.
- **Sentinel-1 SAR** (via Copernicus Open Access Hub or Sentinel Hub free tier) — for U-Net flood extent. 30,000 free processing units per month on Sentinel Hub.

### 5.3 Cyclones
- **IMD (India Meteorological Department)** — cyclone bulletins, public website + RSS feeds.
- **IBTrACS** (NOAA) — historical cyclone tracks for any retrospective analysis.
- **Open-Meteo** — wind fields, pressure.

### 5.4 Wildfires
- **NASA FIRMS** — VIIRS and MODIS active fire detections, near-real-time, free API with registration.

### 5.5 Landslides
- **GSI (Geological Survey of India)** — landslide hazard zonation maps. Used as static overlay.
- **IMD rainfall** — used with published threshold rules (e.g., Aleotti 2004 type curves adapted to Indian basins).

### 5.6 Damage assessment
- **User upload** — drone or smartphone images, processed in-place.
- **xView2 / xBD dataset** — for any future fine-tuning. Not used in v1.

### 5.7 Citizen reports
- **In-app SOS form** — primary channel.
- **Public Twitter/X via Nitter** — optional, scraped read-only, geofenced to India. Add later.

---

## 6. AI / ML Models

### 6.1 Earthquake — Seismic Anomaly Detection and Aftershock Probability

**Inputs:** Rolling window of USGS event catalog for a region (last 30 days), plus optional waveform features for stations near the user-selected area.

**Models:**
1. **LSTM Autoencoder** — reconstructs the expected next-event interval and magnitude distribution; anomaly score = reconstruction error normalized by historical baseline.
2. **Omori law fit** — for aftershock probability after any M ≥ 4.5 event in the region. Standard form: `n(t) = K / (c + t)^p`. Fit `K`, `c`, `p` on the first 24 hours of aftershock catalog.
3. **LLM characterization** — Qwen2.5-7B receives the event JSON and writes a 2–3 sentence plain-language summary including tsunami risk flag.

**Training data:** 5+ years of USGS catalog for the Indian subcontinent + adjacent plate boundaries (Indian Plate, Eurasian Plate, Burma micro-plate). Pull via USGS API once, store as Parquet on R2.

**Output:** `anomaly_score` (0–1), `aftershock_24h_probability` (0–1), `aftershock_7d_probability` (0–1), `explanation` (string), `tsunami_risk` (boolean from USGS field).

**Important honesty note:** This is **not earthquake prediction** in the deterministic "earthquake X will happen at time Y" sense — which does not exist as working science. See Section 17.

### 6.2 Flood — Discharge Forecast and Extent Segmentation

**Discharge forecast (LSTM):**
- **Inputs:** CWC gauge reading sequence (last 48 hours, hourly), upstream rainfall (Open-Meteo, last 72 hours + 72-hour forecast), basin static features (area, slope, soil index from HydroSHEDS).
- **Architecture:** 2-layer LSTM, hidden size 64, sequence-to-sequence with 72-hour output horizon.
- **Training data:** 5+ years of CWC + IMD data for 5 starter basins (Krishna, Godavari, Mahanadi, Yamuna, Brahmaputra).
- **Output:** Hourly discharge prediction for next 72 hours with 10th/50th/90th percentile bands.

**Flood extent (U-Net):**
- **Inputs:** Sentinel-1 VV+VH SAR composite tile (256×256 pixels at 10 m resolution).
- **Architecture:** Standard U-Net with 4 down/up blocks, output is binary water mask.
- **Training data:** Per the Enipeas Basin paper methodology — synthetic flood extents from HEC-RAS 2D as ground truth, plus real Sentinel-1 captures during the 2018 Kerala flood and 2023 Sikkim flash flood for validation.
- **Output:** Per-pixel flood probability mask.

**Validation:** CWC readings and official flood bulletins are stored with provenance. If future partner feeds are added, they must be documented and validated before they can affect severity.

### 6.3 Cyclone — Track Extrapolation

v1: rule-based extrapolation from IMD bulletin coordinates over 12-hour horizons, plus impact-zone estimation as a circle of radius `R(category)`. v2: proper CNN-LSTM track model trained on IBTrACS — out of scope for the 1-month build.

### 6.4 Wildfire — FIRMS Clustering

v1: DBSCAN clustering of FIRMS hotspots within last 24 hours; risk classification by cluster size and fire radiative power. v2: ConvLSTM susceptibility map per the Republic of Congo paper methodology.

### 6.5 Landslide — Rainfall Threshold

v1: published intensity-duration thresholds applied to Open-Meteo rainfall, overlaid on GSI hazard zones. v2: XGBoost susceptibility model.

### 6.6 SOS Triage

- **Geolocation extraction:** spaCy `en_core_web_trf` plus a small custom NER trained on Indian place names; fallback to GeoNames lookup.
- **Urgency scoring:** Qwen2.5-7B prompted to score 1–5 on a fixed rubric (1 = information request, 5 = imminent life threat). After 500 labeled examples are collected, replace with a fine-tuned DistilBERT classifier.
- **Multilingual:** Qwen2.5 handles Hindi natively; for Telugu/Tamil/Bengali, fall back to a translation step via IndicTrans2.

### 6.7 Damage Assessment

v1: pretrained DeepLabV3 (segmentation-models-pytorch) on uploaded images. Detects "building," "road," "water," "vegetation." No fine-tuning — clearly labeled as preview.

---

## 7. Local LLM Strategy

### 7.1 Hardware reality

RTX 3060 (8 GB or 12 GB VRAM variants) + 16 GB system RAM. A Q4_K_M quantized 7B model fits with headroom for context (4K–8K tokens). Larger models force aggressive quantization that degrades quality.

### 7.2 Model choice

**Qwen2.5-7B-Instruct (Q4_K_M)** is the primary. Reasons:
- Apache 2.0 license — commercial use allowed.
- Multilingual including Hindi, Tamil, Bengali — critical for Indian SOS triage.
- Strong tool-use / function-calling support — useful when LLM has to call backend APIs to fetch data.
- 32K context window — enough to stuff a full event JSON plus instruction.

### 7.3 Runtime

- **Development:** Ollama. One command to install, one command to pull, simple API. `ollama run qwen2.5:7b`.
- **Production-style:** llama.cpp server compiled with CUDA. Slightly faster, gives you fine-grained control of context length, sampling, batching.

### 7.4 Exposure to public dashboard

Your PC is the LLM host. Cloudflare Tunnel exposes `http://localhost:11434` (Ollama port) as `https://alertix-llm.<your-subdomain>.trycloudflare.com` over a free tunnel. The backend on Render calls this URL. When your PC is off, the backend detects timeout and falls back to Groq.

### 7.5 Fallback ladder

```
Request → Local Qwen (Ollama via tunnel)
        → if timeout/error → Groq Llama 3.1 70B
        → if rate-limited  → Gemini 1.5 Flash (Google AI Studio free tier)
        → if all fail      → static templated response, mark explanation_status='degraded'
```

Always degrade gracefully. The dashboard must never block on the LLM.

### 7.6 Fine-tuning roadmap

Not in the 1-month scope. When you have 500+ labeled SOS triage examples, LoRA-tune Qwen with Unsloth on the same RTX 3060. Expect 6–10 hours of training time. This unlocks (a) better Indian-context understanding, (b) more consistent urgency scoring, (c) brand-aligned output style.

---

## 8. Database Schema

PostgreSQL 15 with PostGIS extension. All timestamps in UTC. SRID 4326 for geography.

```sql
-- Users handled by Supabase Auth (auth.users)
-- App-side extension table:

CREATE TABLE profiles (
    user_id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name       TEXT,
    role            TEXT NOT NULL DEFAULT 'citizen',  -- 'citizen'|'official'|'admin'
    home_location   GEOGRAPHY(POINT, 4326),
    preferred_lang  TEXT DEFAULT 'en',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Every hazard event, normalized
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hazard_type     TEXT NOT NULL,    -- earthquake|flood|cyclone|wildfire|landslide|damage
    source          TEXT NOT NULL,    -- usgs|iris|imd_rsmc|jtwc|nasa_firms|cwc|open_meteo|user
    external_id     TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL,
    location        GEOGRAPHY(POINT, 4326),
    region          GEOGRAPHY(POLYGON, 4326),
    magnitude       FLOAT,
    depth_km        FLOAT,
    intensity       FLOAT,
    metadata        JSONB,            -- source-specific raw fields
    anomaly_score   FLOAT,
    probability     FLOAT,
    model_version   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (source, external_id)
);
CREATE INDEX events_location_idx ON events USING GIST (location);
CREATE INDEX events_region_idx ON events USING GIST (region);
CREATE INDEX events_occurred_idx ON events (occurred_at DESC);
CREATE INDEX events_hazard_idx ON events (hazard_type);

-- Alerts generated by the system
CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hazard_type     TEXT NOT NULL,
    severity        TEXT NOT NULL,    -- info|watch|warning|emergency
    region          GEOGRAPHY(POLYGON, 4326),
    title           TEXT NOT NULL,
    explanation     TEXT,
    explanation_lang TEXT DEFAULT 'en',
    explanation_status TEXT DEFAULT 'pending',  -- pending|done|degraded
    probability     FLOAT,
    event_ids       UUID[],
    model_version   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ
);
CREATE INDEX alerts_region_idx ON alerts USING GIST (region);
CREATE INDEX alerts_created_idx ON alerts (created_at DESC);

-- Citizen SOS reports
CREATE TABLE sos_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    raw_text        TEXT NOT NULL,
    language        TEXT,
    location        GEOGRAPHY(POINT, 4326),
    extracted_location_text TEXT,
    urgency_score   FLOAT,
    triaged         BOOLEAN DEFAULT false,
    llm_summary     TEXT,
    related_event_id UUID REFERENCES events(id),
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX sos_location_idx ON sos_reports USING GIST (location);
CREATE INDEX sos_urgency_idx ON sos_reports (urgency_score DESC);

-- Audit log — mandatory for any future govt/insurer pilot
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id   UUID,
    action          TEXT NOT NULL,
    target_table    TEXT,
    target_id       UUID,
    payload         JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Model registry — track which model produced which prediction
CREATE TABLE model_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name      TEXT NOT NULL,    -- 'seismic_autoencoder'|'flood_lstm'|...
    version         TEXT NOT NULL,
    trained_at      TIMESTAMPTZ NOT NULL,
    metrics         JSONB,
    artifact_url    TEXT,             -- R2 path to weights
    is_active       BOOLEAN DEFAULT false,
    UNIQUE (model_name, version)
);

-- Region reference — Indian states, districts, basins
CREATE TABLE regions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    region_type     TEXT NOT NULL,    -- state|district|basin|grid_cell
    parent_id       UUID REFERENCES regions(id),
    geometry        GEOGRAPHY(MULTIPOLYGON, 4326) NOT NULL,
    metadata        JSONB
);
CREATE INDEX regions_geom_idx ON regions USING GIST (geometry);
CREATE INDEX regions_type_idx ON regions (region_type);
```

---

## 9. API Surface

All routes return JSON. Authentication via Supabase JWT in `Authorization: Bearer <token>` header. Public endpoints marked explicitly.

### 9.1 Auth (via Supabase, not Alertix code)
- `POST /auth/v1/signup` (Supabase managed)
- `POST /auth/v1/token` (Supabase managed)

### 9.2 Events
- `GET /api/events` — list events, filters: `hazard_type`, `from`, `to`, `bbox`, `severity`. Public.
- `GET /api/events/{id}` — single event detail. Public.
- `GET /api/events/recent` — convenience endpoint for last 24h. Public.

### 9.3 Alerts
- `GET /api/alerts` — list active alerts. Public.
- `GET /api/alerts/{id}` — alert detail with LLM explanation. Public.
- `GET /api/alerts/region?lat=&lon=&radius_km=` — alerts near a point. Public.

### 9.4 SOS
- `POST /api/sos` — submit citizen report. Auth optional (anonymous allowed but rate-limited).
- `GET /api/sos/mine` — current user's submissions. Auth required.
- `GET /api/sos/feed` — official-role feed of high-urgency reports. Auth + role required.

### 9.5 Predictions
- `GET /api/predict/earthquake?lat=&lon=&radius_km=` — anomaly score, aftershock probability if recent mainshock, recent activity summary.
- `GET /api/predict/flood?basin_id=` — 72-hour discharge forecast with bands.
- `GET /api/predict/cyclone?storm_id=` — track extrapolation.
- `GET /api/predict/wildfire?bbox=` — clustered hotspot risk.
- `GET /api/predict/landslide?lat=&lon=` — threshold-rule output + GSI zone.

### 9.6 Ingestion (internal, protected)
- `POST /internal/ingest/usgs` — header `X-Cron-Token`. Called by GitHub Actions cron.
- `POST /internal/ingest/firms`
- `POST /internal/ingest/imd`
- `POST /internal/ingest/cwc`
- `POST /internal/ingest/flood`
- `POST /internal/ingest/weather`
- `POST /internal/ingest/cyclones`

### 9.7 LLM (internal)
- `POST /internal/llm/explain` — payload: `event_id`, `lang`. Returns explanation, writes back to events/alerts table.
- `POST /internal/llm/triage_sos` — payload: `sos_id`. Returns urgency + summary, writes back.

### 9.8 WebSocket
- `WS /ws/alerts` — real-time push of new alerts. Public.
- `WS /ws/events?hazard_type=earthquake` — real-time push of new events by type. Public.

### 9.9 Damage
- `POST /api/damage/segment` — multipart upload, returns segmentation mask PNG + class counts. Auth required.

---

## 10. Frontend Specification

### 10.1 Page list

| Route | Purpose | Auth | Notes |
|---|---|---|---|
| `/` | Landing | none | Three.js earth + project intro |
| `/about` | About | none | Capabilities, accuracy, scope, team |
| `/contact` | Contact | none | Form + email |
| `/login` | Login | none | Supabase Auth UI |
| `/signup` | Signup | none | Supabase Auth UI |
| `/dashboard` | Dashboard root | required | Country/state/region selector + overview |
| `/dashboard/earthquake` | Earthquake tab | required | Live map, anomaly chart, aftershock panel |
| `/dashboard/flood` | Flood tab | required | Basin forecast, extent overlay |
| `/dashboard/cyclone` | Cyclone tab | required | Track map, impact circle |
| `/dashboard/wildfire` | Wildfire tab | required | FIRMS hotspot cluster map |
| `/dashboard/landslide` | Landslide tab | required | GSI overlay + rainfall threshold |
| `/dashboard/damage` | Damage tab | required | Upload + segmentation result |
| `/dashboard/sos` | SOS feed | required | Citizen reports stream |
| `/dashboard/alerts` | Alerts feed | required | All active alerts, filterable |

### 10.2 Landing page requirements (from your original brief)

- Live moving background (Three.js earth rotating slowly with subtle cracking effect).
- Project tagline: "Real-time multi-hazard intelligence for India."
- Three-card features section (Earthquake, Flood, Multi-hazard).
- Call-to-action: "Open Dashboard" (auth-gated) and "Read the Docs" (link to public doc).

### 10.3 Dashboard region selector

The dashboard prompts (a) country, (b) state, (c) district or basin. This selection scopes every tab. Default to user's home location if set.

### 10.4 Risk gauge component

Reusable. Inputs: `value` (0–100), `label`, `tier_thresholds` (e.g., 0–30 low, 30–70 moderate, 70+ high). Color-coded. Used on every hazard tab.

### 10.5 Real-time updates

Dashboard subscribes to `/ws/alerts` and `/ws/events`. On any new event matching the user's selected region, a toast notification appears and the relevant tab updates without reload.

### 10.6 Offline shell

Service worker caches landing, about, contact, first-aid static content. Dashboard requires connectivity. First-aid card on dashboard works offline (PWA install supported, not required).

---

## 11. Deployment Architecture (Zero-Cost)

```
Local dev machine (RTX 3060):
  ├── Docker compose: Postgres+PostGIS, Redis, FastAPI dev, React dev
  ├── Ollama running Qwen2.5-7B
  └── Cloudflare Tunnel → exposes Ollama at https://alertix-llm.<sub>.trycloudflare.com

Public demo:
  ├── Frontend  → Cloudflare Pages           (free, unlimited bandwidth)
  ├── Backend   → Render free web service    (sleeps after 15 min idle)
  ├── Database  → Supabase free              (Postgres+PostGIS, 500 MB)
  ├── Cache     → Upstash Redis free         (256 MB)
  ├── Storage   → Cloudflare R2 free         (10 GB)
  ├── LLM       → Local Qwen via tunnel + Groq fallback
  ├── Cron      → GitHub Actions scheduled workflows
  ├── Monitor   → Grafana Cloud + Sentry (both free)
  └── Email     → Resend free                (100/day)
```

### 11.1 Wake-on-cron pattern for free Render

Render free instances sleep after 15 minutes of inactivity. To keep ingestion fresh:

- GitHub Actions cron runs every 5 minutes.
- It POSTs to `/internal/ingest/usgs` with a secret header.
- The request wakes the service. First request after sleep takes ~30–60 seconds; subsequent are fast.
- Set GitHub Actions timeout to 90 seconds to absorb cold start.

### 11.2 LLM availability

Your local PC is online → primary LLM is Qwen. Your PC is off → backend's call times out in 5 s → fallback to Groq → if Groq rate-limited → fallback to Gemini → if all fail → templated explanation marked `explanation_status='degraded'`.

### 11.3 Budget envelope

Total monthly cost target: ₹0. Realistic ceiling once you cross free tiers (≈100 daily active users): ₹1,500–₹2,500/month on Hetzner CPX31 + a managed Postgres.

---

## 12. Phase-Wise Build Plan

Four weeks, ~37 hours per week, ~150 productive hours total. Plan for a week-5 buffer.

### Phase 0 — Pre-Flight (Day 0, ~4 hours)

**Goal:** environment ready before week 1 starts.

Tasks:
1. Install: Docker Desktop, Node 20 LTS, Python 3.11, Git, VS Code.
2. Sign up: GitHub (private repo `alertix-ai`), Supabase, Upstash, Cloudflare, Render, Groq, Sentry, Resend.
3. Install Ollama, pull `qwen2.5:7b` and `nomic-embed-text`.
4. Verify GPU: `ollama run qwen2.5:7b "hello"` should respond in under 5 seconds.
5. Create Cloudflare Tunnel for your Ollama port (do this once, save the URL).
6. Initialize repo with the structure in Section 13. Push to GitHub.
7. Write `.env.example` and `README.md` skeleton.

**Exit criteria:** `docker compose up` brings up Postgres, Redis, empty FastAPI; `curl http://localhost:8000/health` returns `{"status":"ok"}`.

---

### Phase 1 — Foundation (Week 1)

**Goal:** end-to-end live USGS earthquake data appears on a deployed Leaflet map. This is the spine of the entire project.

#### Day 1–2: Backend skeleton

- FastAPI app with `/health` and `/version`.
- SQLAlchemy + Alembic configured against Supabase.
- Apply initial migration creating `events`, `alerts`, `sos_reports`, `profiles`, `audit_log`, `model_versions`, `regions` tables.
- Pydantic schemas for Event, Alert, SOS.
- Supabase Auth JWT verification middleware.

#### Day 3: USGS ingestion

- `app/ingestion/usgs.py` — pull GeoJSON, normalize to Event.
- `app/api/internal_ingest.py` — POST endpoint with cron token.
- Upsert by `(source, external_id)` so reruns are idempotent.
- Manual test: `curl -X POST -H "X-Cron-Token: $TOKEN" http://localhost:8000/internal/ingest/usgs`.

#### Day 4: Frontend skeleton

- Vite + React + TypeScript + Tailwind + shadcn/ui scaffolded.
- Routes set up via React Router: Landing, About, Contact, Login, Signup, Dashboard.
- Supabase JS client configured. Login/Signup pages working against Supabase Auth.
- Empty Dashboard with sidebar showing all 6 hazard tabs.

#### Day 5: Map + first hazard view

- `components/Map.tsx` wrapping React-Leaflet with OSM tiles.
- `/dashboard/earthquake` calls `GET /api/events?hazard_type=earthquake` and plots last 24h on map.
- Marker color/size by magnitude.
- Click marker → popup with details + link to USGS.

#### Day 6: Deployment

- Push backend to Render free web service. Connect Supabase DATABASE_URL.
- Push frontend to Cloudflare Pages.
- Set GitHub Actions cron `*/5 * * * *` hitting `/internal/ingest/usgs`.
- Verify public URL shows live earthquakes.

#### Day 7: Buffer + first-time bug fixes.

**Exit criteria:** Public URL displays live earthquakes within 5 minutes of USGS publication. Login/signup work. Dashboard loads.

---

### Phase 2 — Core AI Layer (Week 2)

**Goal:** real AI underneath earthquake and flood hazards; LLM explanations live on dashboard.

#### Day 8–9: Seismic autoencoder training

- Pull 5 years of USGS catalog for Indian region (`minlat=5, maxlat=40, minlon=65, maxlon=100`).
- Feature engineering: rolling 30-day windows of (count, mean_mag, max_mag, depth_stats, inter-event time).
- Train LSTM autoencoder in PyTorch on RTX 3060. Save weights to R2.
- Register model in `model_versions` table, mark active.
- `app/ml/seismic_autoencoder.py` — inference function.
- New endpoint `GET /api/predict/earthquake?lat=&lon=&radius_km=`.

#### Day 10: Aftershock probability + dashboard panel

- Implement Omori law fitter (scipy.optimize.curve_fit).
- On every M ≥ 4.5 event ingestion, trigger aftershock fit job.
- Dashboard earthquake tab: add anomaly time-series chart (Recharts) and aftershock probability gauge.

#### Day 11: Ollama integration

- `app/llm/ollama_client.py` — async HTTP client to your tunneled Ollama URL.
- `app/llm/groq_client.py` — fallback.
- `app/llm/provider.py` — interface with fallback ladder.
- `app/llm/prompts.py` — prompt templates: `EARTHQUAKE_EXPLAIN`, `FLOOD_EXPLAIN`, `SOS_TRIAGE`.
- `POST /internal/llm/explain` endpoint.
- Background task: when a new alert is created, queue an LLM explanation job.

#### Day 12: SOS form + geolocation

- `/dashboard/sos` page with form (text, optional location pin).
- `POST /api/sos`.
- spaCy NER for location extraction; Nominatim lookup; fallback to GeoNames.
- LLM triage scoring 1–5.
- Display in SOS feed.

#### Day 13: WebSocket

- `WS /ws/alerts` and `WS /ws/events`.
- Redis pub/sub bridge.
- Frontend uses TanStack Query for initial load, WebSocket for live updates.

#### Day 14: Buffer.

**Exit criteria:** New USGS event triggers (a) DB write, (b) anomaly score, (c) LLM-explained alert if severity high, (d) WebSocket push to dashboard, all within 90 seconds.

---

### Phase 3 — Multi-Hazard Expansion (Week 3)

**Goal:** flood, cyclone, wildfire, landslide, damage tabs all surfacing real data.

#### Day 15: Flood data pipeline

- CWC and configured official flood bulletin integration.
- CWC scraper for 5 starter basins (Krishna, Godavari, Mahanadi, Yamuna, Brahmaputra). Use BeautifulSoup, respect robots.
- Open-Meteo rainfall integration.
- All flood events into `events` table.

#### Day 16: Flood LSTM discharge model

- Pull historical CWC + IMD data for Krishna basin (your home basin, easiest validation).
- Train 2-layer LSTM in PyTorch. Save to R2.
- `GET /api/predict/flood?basin_id=` returns 72-hour forecast with bands.
- Flood tab: line chart with confidence bands, basin map overlay.

#### Day 17: U-Net flood extent (preview)

- Use a pretrained Sentinel-1 water segmentation U-Net (or train a small one on the public Sen1Floods11 dataset, which is free).
- Endpoint accepts a bbox, fetches latest Sentinel-1 tile, runs U-Net, returns GeoJSON polygons.
- Display as Leaflet overlay on flood tab.

#### Day 18: Cyclone tab

- IMD bulletin RSS scraper.
- Parse current cyclone position, intensity, projected track.
- Plot track on Leaflet with impact-radius circle.

#### Day 19: Wildfire tab

- NASA FIRMS API integration.
- DBSCAN cluster hotspots in the last 24 hours.
- Display clusters on map with size = hotspot count, color = fire radiative power.

#### Day 20: Landslide tab

- Load GSI landslide hazard zonation as static GeoJSON overlay.
- Apply intensity-duration rainfall threshold rule on Open-Meteo data.
- Highlight high-risk districts.

#### Day 21: Damage assessment tab

- Image upload form.
- Backend runs DeepLabV3 on uploaded image.
- Returns segmentation mask + class breakdown.

**Exit criteria:** All 6 hazard tabs functional with live or recent real data and at least basic interactivity.

---

### Phase 4 — Polish and Production (Week 4)

**Goal:** demo-ready, monitored, secure, with pitch materials.

#### Day 22: Landing page

- Three.js rotating earth with subtle "shattering" effect (use a noise-based displacement shader; reuse an open-source example).
- Animated headline, three feature cards, footer.
- Optimize bundle size — Three.js + GLTF can balloon; use draco compression.

#### Day 23: About + Contact pages

- About: services, capabilities, accuracy disclaimers, technology summary, scope statement copied from Section 2 of this doc.
- Contact: form posts to `POST /api/contact`, triggers Resend email.

#### Day 24: Risk scoring fusion

- XGBoost model: features = outputs of all hazard sub-models for a region; label = self-supervised (recent severity).
- Composite "Alertix Risk Index" per district, 0–100.
- Display on dashboard home as heatmap.

#### Day 25: Hardening

- Rate limiting on public endpoints (slowapi).
- Sentry integration across backend and frontend.
- Grafana dashboards for: ingestion lag per source, LLM fallback rate, alert generation rate, API p95 latency.
- Audit log writes on every alert and SOS triage.

#### Day 26: Testing pass

- pytest for backend ingestion + model inference paths.
- Vitest for critical frontend components (Map, AlertCard, RiskGauge).
- One Playwright e2e: signup → dashboard → see live alert.

#### Day 27: Demo content

- Record 3-minute demo video using OBS.
- Generate pitch deck (10 slides): problem, solution, demo, architecture, data sources, AI/ML, differentiation, scope honesty, roadmap, ask.
- Write public README with badges, screenshots, deployment URL.

#### Day 28: Buffer + launch.

**Exit criteria:** Public deployed URL, demo video, pitch deck, monitored ops, documented APIs, working in front of a stranger without you in the room.

---

### Phase 5 — Post-Launch Roadmap (Weeks 5+)

Not committed to v1 but listed here so the pitch deck has substance.

| Theme | Items |
|---|---|
| Better models | Proper ConvLSTM for wildfire; CNN-LSTM cyclone track; XGBoost landslide; Pangu/GraphCast initialization for cyclones |
| Coverage | More basins; SE Asia neighbors; tsunami module via DART buoy data |
| Mobile | Native React Native app with push notifications |
| Hardware | ESP32 + MPU6050 community seismic sensors per your original brief |
| Agency integration | NDRF/SDMA API hooks; standardized CAP-protocol alert output |
| LLM | LoRA fine-tune on Indian SOS dataset once 500+ labels exist |
| Multilingual | IndicTrans2 pipeline for full Hindi/Telugu/Tamil/Bengali/Marathi coverage |
| Damage | Fine-tune xView2 damage classifier; drone-fleet integration |
| Routing | Real evacuation routing with damage-aware OSRM custom profile |
| Compliance | DPDPA-compliant consent flows; SOC2 prep |

---

## 13. Repository Structure

```
alertix-ai/
├── docker-compose.yml
├── .env.example
├── README.md
├── ALERTIX_AI_DOCUMENTATION.md
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── auth/
│   │   │   └── deps.py
│   │   ├── models/
│   │   │   ├── event.py
│   │   │   ├── alert.py
│   │   │   ├── sos.py
│   │   │   ├── profile.py
│   │   │   └── region.py
│   │   ├── schemas/
│   │   ├── api/
│   │   │   ├── events.py
│   │   │   ├── alerts.py
│   │   │   ├── sos.py
│   │   │   ├── predict.py
│   │   │   ├── damage.py
│   │   │   ├── internal_ingest.py
│   │   │   ├── internal_llm.py
│   │   │   └── contact.py
│   │   ├── ingestion/
│   │   │   ├── usgs.py
│   │   │   ├── iris.py
│   │   │   ├── earthquake/
│   │   │   ├── flood/
│   │   │   ├── cyclone/
│   │   │   ├── wildfire/
│   │   │   ├── weather/
│   │   │   └── open_meteo.py
│   │   ├── ml/
│   │   │   ├── seismic_autoencoder.py
│   │   │   ├── aftershock_omori.py
│   │   │   ├── flood_lstm.py
│   │   │   ├── flood_unet.py
│   │   │   ├── wildfire_cluster.py
│   │   │   ├── landslide_rules.py
│   │   │   ├── damage_segment.py
│   │   │   └── geolocation.py
│   │   ├── llm/
│   │   │   ├── provider.py
│   │   │   ├── ollama_client.py
│   │   │   ├── groq_client.py
│   │   │   ├── gemini_client.py
│   │   │   └── prompts.py
│   │   ├── ws/
│   │   │   └── alerts.py
│   │   └── tasks/
│   │       └── scheduler.py
│   ├── scripts/
│   │   ├── train_seismic_autoencoder.py
│   │   ├── train_flood_lstm.py
│   │   ├── seed_regions.py
│   │   └── backfill_usgs.py
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── Landing.tsx
│   │   │   ├── About.tsx
│   │   │   ├── Contact.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Signup.tsx
│   │   │   └── Dashboard/
│   │   │       ├── index.tsx
│   │   │       ├── EarthquakeTab.tsx
│   │   │       ├── FloodTab.tsx
│   │   │       ├── CycloneTab.tsx
│   │   │       ├── WildfireTab.tsx
│   │   │       ├── LandslideTab.tsx
│   │   │       ├── DamageTab.tsx
│   │   │       ├── SosTab.tsx
│   │   │       └── AlertsTab.tsx
│   │   ├── components/
│   │   │   ├── Map.tsx
│   │   │   ├── AlertCard.tsx
│   │   │   ├── RiskGauge.tsx
│   │   │   ├── RegionSelector.tsx
│   │   │   ├── ThreeEarth.tsx
│   │   │   └── ui/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── ws.ts
│   │   │   ├── supabase.ts
│   │   │   └── types.ts
│   │   └── styles/
│   └── public/
│
├── ml/
│   ├── notebooks/
│   │   ├── 01_seismic_autoencoder.ipynb
│   │   ├── 02_flood_lstm.ipynb
│   │   └── 03_flood_unet.ipynb
│   ├── data/         (gitignored)
│   └── models/       (gitignored, weights on R2)
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy-backend.yml
│       ├── deploy-frontend.yml
│       ├── cron-usgs.yml
│       ├── cron-firms.yml
│       ├── cron-imd.yml
│       ├── cron-cwc.yml
│       └── cron-google-flood-hub.yml
│
└── docs/
    ├── architecture.md
    ├── api.md
    ├── data-sources.md
    ├── runbook.md
    └── pitch.md
```

---

## 14. Security and Privacy

### 14.1 Authentication and authorization
- Supabase Auth with JWT. Row-level security (RLS) policies on `profiles`, `sos_reports`.
- Three roles: `citizen` (default), `official` (verified emergency personnel), `admin`.
- Internal endpoints (`/internal/*`) require `X-Cron-Token` header secret.

### 14.2 PII handling
- SOS submissions may contain PII (names, locations, health status).
- Encrypt at rest via Supabase default.
- Hash IP addresses on logging (never store raw).
- Per Digital Personal Data Protection Act 2023, add consent checkbox on SOS form.
- Right to deletion: implement `DELETE /api/sos/mine/{id}`.

### 14.3 Rate limiting
- Public endpoints: 60 req/min per IP (slowapi).
- SOS submission: 5/hour per IP for anonymous, 30/hour for authenticated.

### 14.4 Secrets management
- All keys in environment variables. Never committed.
- Use Render env vars for backend. Cloudflare Pages env vars for frontend.
- Rotate `CRON_TOKEN` quarterly.

### 14.5 Audit
- Every alert generation, every SOS triage, every model inference goes to `audit_log`.
- Mandatory for any government or insurance pilot.

### 14.6 Disclaimers
- Every page footer: "Alertix AI provides hazard intelligence for situational awareness. It is not a substitute for official warnings from IMD, NCS, NDRF, or state authorities. Do not rely on Alertix AI for life-safety decisions."

---

## 15. Pitfalls and Failure Modes

Real things that will go wrong. Mitigations included.

| Pitfall | Probability | Mitigation |
|---|---|---|
| Render service sleeps mid-demo | High | Warm with `curl` 5 min before any demo |
| Supabase 500 MB DB full | Medium | Archive events older than 90 days to R2 as Parquet |
| Local PC off → LLM unavailable | High | Groq fallback (already in design) |
| Groq rate-limited | Medium | Gemini Flash fallback (already in design) |
| Cloudflare Tunnel URL changes | Medium | Use named tunnel with stable hostname |
| CWC scraping blocked | Medium | Cache last good values; alert operators and use configured official bulletins only |
| GitHub Actions cron drift | Low | Add health-check endpoint that reports last-ingest age |
| Three.js earth crashes mobile Safari | Medium | Serve a static fallback hero image to mobile detection |
| Sentinel Hub processing units exhausted | Medium | Cache extent results aggressively; serve preview only on flood tab |
| Misinformation in SOS submissions | High | Surface raw text; do not auto-issue public alerts from a single SOS |
| Earthquake "prediction" challenged by users | High | Section 17 disclaimer on every earthquake panel |

---

## 16. Pitch Positioning

### 16.1 The one-line
"Alertix AI is real-time multi-hazard intelligence for India — earthquake, flood, cyclone, wildfire, landslide, and damage assessment — built on open data and deployable on a single server."

### 16.2 The three differentiators
1. **Open-source, on-premise deployable.** State DMAs and insurers cannot pay watsonx prices. We give them an option that runs on a ₹50,000 box.
2. **Multilingual citizen-report triage.** Indian disasters generate Hindi, Telugu, Tamil, Bengali SOS messages. Incumbents are English-only.
3. **Scope honesty.** We tell customers what we don't do. That wins enterprise trust faster than feature lists.

### 16.3 The pilot targets (in priority order)
1. A general insurer with parametric flood or seismic products.
2. A state disaster management authority (Telangana SDMA is closest, geographically).
3. A logistics or utility firm with weather-exposed operations.

### 16.4 The ask in any pitch
Free 30-day pilot, on their data, with a measurable success metric defined up front (e.g., median time-to-awareness for floods reduced from X to Y).

---

## 17. Earthquake Prediction — Technical Honesty Note

This section is included by request of the project owner who has decided to label the earthquake module as "earthquake prediction" in the public-facing dashboard and pitch deck. The technical reality follows.

### 17.1 What the scientific consensus says

Deterministic earthquake prediction — answering "when, where, and how big" with operational accuracy — is not currently possible and has not been demonstrated by any system, research lab, or government program. The USGS, the Seismological Society of America, and every peer-reviewed paper referenced in this project's source materials agree on this point. Systems labeled "earthquake early warning" (Japan's J-Alert, USGS ShakeAlert, Mexico's SASMEX) work after a rupture has already begun and provide seconds-to-tens-of-seconds of warning to distant locations before strong shaking arrives.

### 17.2 What Alertix AI actually does

Despite the user-facing label, the earthquake module performs the following operations, all of which are scientifically defensible:

1. **Real-time monitoring** of global seismicity via USGS feed.
2. **Anomaly detection** via LSTM autoencoder on rolling event-statistics windows. Anomaly scores indicate that recent activity is statistically unusual relative to a baseline; they do not predict that a specific earthquake will occur.
3. **Aftershock probability estimation** via Omori-law fitting, after a mainshock has occurred. This is well-established science.
4. **Rapid event characterization** via LLM, producing plain-language summaries of magnitude, depth, tsunami risk, etc.

### 17.3 Risks the project owner has accepted

- Technical credibility loss with geophysicists, seismologists, and academic reviewers.
- Difficulty securing pilot contracts with USGS-aware government bodies, insurance underwriters, and risk modelers.
- Possible liability exposure if users make life-safety decisions based on the "prediction" label and the system fails to produce a warning before an event.

### 17.4 Recommended mitigation if the label is retained

If "Earthquake Prediction" remains the public label, the following text must appear adjacent to every prediction display:

> *"Alertix AI does not perform deterministic earthquake prediction. The values shown represent statistical anomaly scores and aftershock probabilities derived from recent seismicity. They are not forecasts of specific future events. Always follow official warnings from the National Center for Seismology (NCS) and the IMD."*

This disclaimer is not optional. It is the minimum legal and ethical floor.

---

## 18. Glossary

- **Aftershock** — smaller earthquake following a larger mainshock on the same fault system.
- **Anomaly score** — output of the LSTM autoencoder; reconstruction error normalized to historical baseline.
- **APScheduler** — Python in-process scheduling library; used for periodic ingestion jobs.
- **CAP (Common Alerting Protocol)** — XML standard for emergency alerts.
- **ConvLSTM** — convolutional LSTM, used in wildfire spatiotemporal modeling per the source papers.
- **CWC** — Central Water Commission, India.
- **DBSCAN** — density-based clustering, used for wildfire hotspot grouping.
- **Discharge** — volumetric water flow rate, typically in cubic meters per second.
- **FDSN** — International Federation of Digital Seismograph Networks; provides standard web services for waveform data.
- **FIRMS** — Fire Information for Resource Management System (NASA).
- **GeoJSON** — JSON format for representing geographic features.
- **GIS** — Geographic Information System.
- **GSI** — Geological Survey of India.
- **HEC-RAS** — Hydrologic Engineering Center's River Analysis System; standard hydraulic modeling software.
- **HR-GNSS** — High-Rate Global Navigation Satellite System; used in M-LARGE paper for fault tracking.
- **IBTrACS** — International Best Track Archive for Climate Stewardship; cyclone database.
- **IMD** — India Meteorological Department.
- **IRIS** — Incorporated Research Institutions for Seismology.
- **LoRA** — Low-Rank Adaptation; parameter-efficient fine-tuning method.
- **LSTM** — Long Short-Term Memory neural network; used for time-series forecasting.
- **MMI** — Modified Mercalli Intensity; earthquake shaking scale.
- **NCS** — National Center for Seismology, India.
- **NDRF** — National Disaster Response Force, India.
- **Omori law** — empirical decay law for aftershock rate over time.
- **OSM** — OpenStreetMap.
- **PEGS** — Prompt Elastogravity Signals; speed-of-light gravity perturbations from earthquakes.
- **PostGIS** — geospatial extension to PostgreSQL.
- **PWA** — Progressive Web App.
- **RLS** — Row-Level Security (Postgres / Supabase feature).
- **SAR** — Synthetic Aperture Radar; the Sentinel-1 satellite uses this.
- **SDMA** — State Disaster Management Authority.
- **SOS** — distress signal; here, citizen-submitted distress reports.
- **U-Net** — convolutional segmentation network; standard for flood-extent mapping.
- **USGS** — United States Geological Survey.
- **VIIRS** — Visible Infrared Imaging Radiometer Suite; satellite instrument used by FIRMS.
- **WebSocket** — full-duplex communication protocol used for real-time dashboard updates.
- **xView2** — building damage assessment satellite dataset.

---

*End of document.*


this doc is the  of the main execution for my life i want to run it and make it one of my better things and better and 