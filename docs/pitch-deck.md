# Alertix AI — 10-slide pitch deck

> Speaker notes follow each slide. One H1 per slide so any Markdown→slides tool
> (Marp, Pandoc-Beamer, Reveal.js, Slidev) renders this cleanly.
> Quick render: `marp docs/pitch-deck.md --pdf` or `marp docs/pitch-deck.md --pptx`.

---

# 1 · The Problem

- 350M+ Indians live in multi-hazard zones (NDMA 2024)
- IMD, NCS, CWC, FSI, GSI each publish in **isolation** — no unified picture
- Citizens get alerts in English only, often hours late
- Insurers and state DMAs lack ML-grade real-time intelligence at a price they can pay

> Notes: open with the 2023 Sikkim GLOF — 4 different agencies issued partial warnings; none reached the affected villages in time.

---

# 2 · The Solution

**Alertix AI** — one real-time platform fusing every Indian hazard feed with on-device ML.

- Live map: earthquake · flood · cyclone · wildfire · landslide
- AI-generated alerts in plain language, 4 Indic languages
- Citizen SOS triaged in seconds with NER + geocoding
- Composite **Risk Index** per district, updated every 30s

---

# 3 · Live Demo

1. India dashboard — 2,000+ live events, last 24h
2. Click an earthquake → LSTM anomaly score + Omori aftershock probability
3. Submit Hindi SOS "हैदराबाद में बाढ़" → triaged + geocoded in <5s
4. Toggle Risk Heatmap overlay → see Critical zones lit up

> Notes: keep this slide as a screen-recording fallback; never live-demo SOS rate limits.

---

# 4 · Architecture

```
[USGS · IMD · CWC · FIRMS · IRIS · Sentinel-1]
                  │
          [Ingestion workers]
                  │
        [PostGIS + Redis Streams]
                  │
   ┌──────────────┼──────────────┐
   │              │              │
[ML inference]  [LLM ladder]   [WebSocket fanout]
   │              │              │
   └──────────────┼──────────────┘
                  │
       [React + Leaflet frontend]
```

- 100% open-source stack · single-box deployable · Render + Cloudflare free tier today

---

# 5 · Data sources (all free, non-commercial)

| Hazard | Primary | Backup |
|---|---|---|
| Earthquake | USGS GeoJSON | IRIS waveforms |
| Flood | CWC FFM dashboard | Open-Meteo |
| Cyclone | IMD/RSMC bulletins | JTWC ATCF |
| Wildfire | NASA FIRMS | Sentinel-2 NDVI |
| Landslide | GSI hazard zonation | Open-Meteo rainfall |
| Damage | Sentinel-1 GRD SAR | Citizen photos |

---

# 6 · AI/ML models in production today

| Model | Purpose | Status |
|---|---|---|
| Seismic LSTM autoencoder | Anomaly score on 30-event sequences | ✅ trained on 5yr USGS India |
| Omori aftershock | 24h / 7d probability per mainshock | ✅ analytic |
| Flood LSTM | 24/48/72h river-level forecast | ✅ trained, RMSE 0.48m |
| Flood U-Net | Sentinel-1 SAR extent segmentation | ✅ IoU 0.93 (synthetic) |
| Wildfire DBSCAN | Hotspot clustering + risk tier | ✅ live |
| Damage CNN | 4-class post-event imagery | ✅ trained |
| Composite XGBoost | Risk Index 0-1 per cell | ✅ val RMSE 0.031 |
| LLM ladder (Cerebras Llama 8B → Groq → Gemini) | Plain-language alerts + SOS triage | ✅ live |

---

# 7 · Differentiation

1. **Open-source, on-prem deployable.** State DMAs can't pay watsonx prices — Alertix runs on a ₹50k box.
2. **Multilingual citizen-report triage.** Hindi · Telugu · Tamil · Bengali — incumbents are English-only.
3. **Scope honesty.** We document what we *don't* do (no deterministic quake prediction, no commercial weather data resale). That wins enterprise trust.

---

# 8 · Scope honesty

- We do **not** predict individual earthquakes — only anomaly/aftershock probabilities
- We do **not** replace IMD or CWC — we fuse and amplify their bulletins
- We do **not** store raw IPs or PII beyond what users explicitly submit (DPDPA 2023 compliant)
- We **do** ship every model behind a feature flag with a graceful degradation path

---

# 9 · Roadmap (next 6 months)

- M1 · Production deploy on Render + Cloudflare Pages · LIVE
- M2 · IndicTrans2 multilingual triage (Hindi → English LLM bridge complete)
- M3 · DistilBERT urgency classifier (collect 500 labeled SOS first)
- M4 · Pilot with 1 SDMA + 1 parametric insurer
- M5 · Mobile PWA + offline-first SOS queue
- M6 · Open public API for OSS responders

---

# 10 · The Ask

**Free 30-day pilot** on your data, with a measurable success metric defined up front.

- Pilot targets (priority): general insurer (parametric flood/seismic) → state DMA → logistics/utility
- Cost to you: zero · Cost to us: server + my time
- Contact: **sreekarkumar1206@gmail.com**

> Notes: close with the demo URL and a single QR code linking to /dashboard.
