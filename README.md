# Alertix AI

**Real-time multi-hazard disaster monitoring, prediction, and early-warning platform for India.**

Six hazard categories — earthquakes, floods, cyclones, wildfires, landslides, and post-disaster damage — ingested from live public sources, scored by purpose-built ML models, explained in plain language by a guarded LLM layer, and surfaced through a unified operational dashboard.

> **Disclaimer:** Alertix AI provides hazard intelligence for situational awareness only. It is **not** a substitute for official warnings from IMD, NCS, NDRF, CWC, or state disaster management authorities. Do not rely on Alertix AI for life-safety decisions.

## Quick Start

```bash
git clone https://github.com/0XSreekar/ALERTIX-AI.git
cd ALERTIX-AI
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
```

Dashboard: http://localhost:5173  
API docs: http://localhost:8000/docs  
Reverse proxy: http://localhost:8080

## What Is Included

| Layer | What it does |
|---|---|
| Ingestion | USGS, NASA FIRMS, CWC, IMD/JTWC, Open-Meteo async ingestion |
| Processing | Redis Streams consumers, state machine, retry/DLQ, priority queue, risk scoring |
| Database | PostgreSQL 15 + PostGIS, idempotent writes, geo indexes, migrations |
| ML | Omori-Utsu, flood LSTM, flood U-Net, damage segmenter, wildfire DBSCAN, cyclone track analysis |
| AI | Ollama -> Groq -> Gemini fallback with grounded RAG guardrails |
| Frontend | React + Vite + Leaflet dashboard with offline alert/report support |
| Ops | Docker Compose, Nginx, Prometheus, Grafana, GitHub Actions image workflow |

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [TECHNICAL.md](TECHNICAL.md)
- [RESEARCH_REPORT.md](RESEARCH_REPORT.md)
- [docs/api.md](docs/api.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/data-sources.md](docs/data-sources.md)
- [docs/runbook.md](docs/runbook.md)

## Core Commands

Backend:

```bash
cd backend
pip install -e ".[dev]"
ruff check . && mypy app/
pytest
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run typecheck
npm run test
npm run build
npm run dev
```

## Safety Boundaries

- ALERTIX does not predict exact earthquake time, place, or magnitude.
- Learned model inference requires real checkpoint weights.
- AI output is labelled AI-generated and is not an official alert.
- Secrets are loaded from environment variables, never hardcoded.
- Internal ingestion endpoints require `X-Cron-Token`.

## License

See [LICENSE](LICENSE).
