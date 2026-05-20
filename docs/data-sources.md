# Data Sources

Full details in Section 5 of `ALERTIX_AI_DOCUMENTATION.md`.

| Source | Hazard | Frequency | Key Required | Module |
|--------|--------|-----------|-------------|--------|
| USGS Earthquake Hazards | Earthquake | every 60s | No | `ingestion/usgs.py` |
| IRIS FDSN | Earthquake (waveforms) | on-demand | No | `ingestion/iris.py` |
| Google Flood Hub | Flood | every 15 min | Yes | `ingestion/google_flood_hub.py` |
| CWC India | Flood (gauges) | every 30 min | No (scraped) | `ingestion/cwc.py` |
| IMD | Cyclone + rainfall | every 30 min | No (RSS) | `ingestion/imd_cyclone.py` |
| NASA FIRMS | Wildfire | every 60 min | Yes (MAP_KEY) | `ingestion/nasa_firms.py` |
| Open-Meteo | Weather (all hazards) | on-demand | No | `ingestion/open_meteo.py` |
| GSI India | Landslide zones | static | No | Static GeoJSON overlay |
| Sentinel-1 SAR | Flood extent | on-demand | Yes (Sentinel Hub) | Phase 2 |

All sources are free for non-commercial use. Verify ToS before any paid pilot.
