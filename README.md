<div align="center">

# ALERTIX-AI

**Real-time multi-hazard disaster monitoring, prediction, and early warning for India.**

Earthquakes · Floods · Cyclones · Wildfires · Landslides · Post-disaster damage

[![License](https://img.shields.io/github/license/0XSreekar/ALERTIX-AI?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/0XSreekar/ALERTIX-AI?style=flat-square)](https://github.com/0XSreekar/ALERTIX-AI/stargazers)
[![Open issues](https://img.shields.io/github/issues/0XSreekar/ALERTIX-AI?style=flat-square)](https://github.com/0XSreekar/ALERTIX-AI/issues)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org/)
[![Docker Compose](https://img.shields.io/badge/docker-compose-2496ED?style=flat-square)](https://docs.docker.com/compose/)

</div>

---

## Why this exists

India is exposed to almost every category of natural hazard, and official warning systems already exist for each of them. The problem is that they are scattered. Earthquake data comes from NCS and USGS, cyclone tracks from IMD and JTWC, river levels from CWC, active fire detections from NASA FIRMS. Each lives on its own portal, in its own format, on its own refresh cycle. None of them tell a district officer or a citizen what the combined picture looks like right now.

ALERTIX-AI pulls those feeds into a single pipeline, scores them with hazard-specific models, has a guarded LLM explain what the numbers mean in plain language, and puts the result on one operational dashboard. It runs entirely on free and public data sources. There are no paid APIs anywhere in the stack.

> **Disclaimer:** ALERTIX-AI provides hazard intelligence for situational awareness only. It is **not** a substitute for official warnings from IMD, NCS, NDRF, CWC, or state disaster management authorities. Do not rely on ALERTIX-AI for life-safety decisions.

---

## Screenshots

<!-- TODO: Replace the placeholders below with real screenshots.
     Save images under docs/images/ and point the table at them.
     A dashboard screenshot is the single biggest factor in whether
     a visitor stars this repo, so this section is worth the effort. -->

| Live hazard dashboard | Alert detail and AI explanation |
| --- | --- |
| _screenshot pending_ | _screenshot pending_ |

---

## Hazard coverage

| Hazard | Live sources | How it is scored |
| --- | --- | --- |
| Earthquakes | USGS, NCS | Omori-Utsu aftershock decay modelling |
| Floods | CWC, Open-Meteo | LSTM level forecasting and U-Net inundation segmentation |
| Cyclones | IMD, JTWC | Track and intensity analysis |
| Wildfires | NASA FIRMS | DBSCAN clustering of active fire detections |
| Landslides | Rainfall and terrain data | Composite risk scoring |
| Post-disaster damage | Satellite and uploaded imagery | Damage segmentation model |

---

## Quick start

```bash
git clone https://github.com/0XSreekar/ALERTIX-AI.git
cd ALERTIX-AI
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
```

| Service | URL |
| --- | --- |
| Dashboard | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Reverse proxy | http://localhost:8080 |

---

## Architecture

| Layer | What it does |
| --- | --- |
| Ingestion | Async pulls from USGS, NASA FIRMS, CWC, IMD/JTWC and Open-Meteo |
| Processing | Redis Streams consumers, state machine, retry and DLQ, priority queue, risk scoring |
| Database | PostgreSQL 15 with PostGIS, idempotent writes, geo indexes, migrations |
| ML | Omori-Utsu, flood LSTM, flood U-Net, damage segmenter, wildfire DBSCAN, cyclone track analysis |
| AI layer | Ollama to Groq to Gemini fallback chain with grounded RAG guardrails |
| Frontend | React, Vite and Leaflet dashboard with offline alert and report support |
| Ops | Docker Compose, Nginx, Prometheus, Grafana, GitHub Actions image workflow |

---

## Local development

**Backend**

```bash
cd backend
pip install -e ".[dev]"
ruff check . && mypy app/
pytest
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run typecheck
npm run test
npm run build
npm run dev
```

---

## Safety boundaries

ALERTIX does not predict the exact time, place or magnitude of an earthquake, and it never claims to. Learned model inference requires real checkpoint weights rather than random initialisation. Every AI-generated output is labelled as such and is never presented as an official alert. Secrets load from environment variables and are never hardcoded. Internal ingestion endpoints require an X-Cron-Token header.

---

## Documentation

| Document | Contents |
| --- | --- |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment |
| [TECHNICAL.md](TECHNICAL.md) | System internals |
| [RESEARCH_REPORT.md](RESEARCH_REPORT.md) | Research background and evaluation |
| [docs/api.md](docs/api.md) | API reference |
| [docs/architecture.md](docs/architecture.md) | Architecture deep dive |
| [docs/data-sources.md](docs/data-sources.md) | Data source catalogue |
| [docs/runbook.md](docs/runbook.md) | Operational runbook |

---

## Contributing

Contributions are welcome, from typo fixes to entirely new hazard connectors. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for setup, branch naming and commit conventions. Security issues should follow [SECURITY.md](SECURITY.md) rather than going into a public issue.

If ALERTIX-AI is useful to you, a star helps other people working on disaster tech find it.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
