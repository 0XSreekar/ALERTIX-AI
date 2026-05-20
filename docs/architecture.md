# Architecture

See Section 3 of `ALERTIX_AI_DOCUMENTATION.md` for the full architecture diagram and rationale.

## Summary

Three-layer architecture:

1. **Ingestion Layer** — pulls from USGS, IRIS, IMD/RSMC, JTWC, NASA FIRMS, CWC, configured official flood bulletins, and Open-Meteo. Normalizes to a common Event schema. Writes to Postgres + pushes to Redis stream `hazard:events`.

2. **Processing Layer** — consumes from Redis stream. Runs hazard-specific models (Phase 2). Creates Alerts when severity thresholds are crossed. Publishes to Redis pub/sub `alerts:new`.

3. **API + Frontend Layer** — FastAPI REST + WebSocket. React dashboard with Leaflet maps. WebSocket server bridges Redis pub/sub to connected clients.

## Key decisions

- **Redis** decouples ingestion from processing and LLM calls. Without it, a slow LLM call blocks ingestion.
- **PostGIS** is non-negotiable: every hazard query is spatial.
- **Supabase Auth** avoids building auth from scratch. JWT + RLS.
- **APScheduler** (local dev) / GitHub Actions cron (production) for periodic ingestion.
