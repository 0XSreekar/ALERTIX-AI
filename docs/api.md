# API Reference

Full surface defined in Section 9 of `ALERTIX_AI_DOCUMENTATION.md`. Interactive docs at `/docs` (dev only).

## Public endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | none | Health check |
| GET | /version | none | Version + env |
| GET | /api/events | none | List events (filters: hazard_type, from, to, bbox) |
| GET | /api/events/recent | none | Last 24h events |
| GET | /api/events/{id} | none | Single event detail |
| GET | /api/alerts | none | List active alerts |
| GET | /api/alerts/{id} | none | Alert detail |
| GET | /api/alerts/region | none | Alerts near lat/lon/radius |
| POST | /api/sos | optional | Submit citizen SOS report |
| GET | /api/sos/mine | required | User's own reports |
| GET | /api/sos/feed | official+ | High-urgency SOS feed |
| DELETE | /api/sos/mine/{id} | required | Delete own report |
| GET | /api/predict/earthquake | none | Anomaly + aftershock |
| GET | /api/predict/flood | none | Basin discharge forecast |
| GET | /api/predict/cyclone | none | Track extrapolation |
| GET | /api/predict/wildfire | none | Hotspot clusters |
| GET | /api/predict/landslide | none | Threshold + GSI zone |
| POST | /api/damage/segment | required | Upload + segmentation |
| POST | /api/contact | none | Contact form |
| WS | /ws/alerts | none | Live alert stream |
| WS | /ws/events?hazard_type= | none | Live events by type |

## Internal endpoints (X-Cron-Token required)

| Method | Path | Description |
|--------|------|-------------|
| POST | /internal/ingest/usgs | Trigger USGS ingestion |
| POST | /internal/ingest/firms | Trigger FIRMS ingestion |
| POST | /internal/ingest/imd | Trigger IMD ingestion |
| POST | /internal/ingest/cwc | Trigger CWC ingestion |
| POST | /internal/ingest/google_flood_hub | Trigger GFH ingestion |
| POST | /internal/llm/explain | Generate alert explanation (Phase 2) |
| POST | /internal/llm/triage_sos | Triage SOS report (Phase 2) |
