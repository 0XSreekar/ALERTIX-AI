# Data Sources

Full details in Section 5 of `ALERTIX_AI_DOCUMENTATION.md`.

| Source | Hazard | Frequency | Key Required | Module |
|--------|--------|-----------|-------------|--------|
| USGS Earthquake Hazards | Earthquake | every 60s | No | `ingestion/usgs.py` |
| IRIS FDSN | Earthquake (waveforms) | on-demand | No | `ingestion/iris.py` |
| CWC India | Flood (gauges) | every 30 min | No (HTML) | `ingestion/flood/` |
| Official state bulletins | Flood | configured | No/varies | `ingestion/flood/` |
| IMD/RSMC | Cyclone | every 30 min | No (HTML) | `ingestion/cyclone/` |
| JTWC | Cyclone | every 30 min | No (text/HTML) | `ingestion/cyclone/` |
| NASA FIRMS | Wildfire | every 60 min | Yes (MAP_KEY) | `ingestion/wildfire/` |
| Open-Meteo | Weather/rainfall | configured | No | `ingestion/weather/` |
| GSI India | Landslide zones | static | No | Static GeoJSON overlay |
| Sentinel-1 SAR | Flood extent | on-demand | Yes (Sentinel Hub) | Phase 2 |

All sources are free for non-commercial use. Verify ToS before any paid pilot.
