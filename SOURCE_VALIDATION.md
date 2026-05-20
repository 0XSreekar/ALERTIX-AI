# Alertix AI Source Validation

## Removed Fake Integration

The previous `google_flood_hub.py` module used:

```text
https://floodhub.google.com/api/v1/gauges
```

That endpoint is not a documented public Google Flood Hub API endpoint, so it has been removed from active ingestion. Phase 1 flood ingestion now uses CWC and configured official bulletin pages only. No mock or invented flood-source response is used.

## Trusted Phase 1 Sources

| Hazard | Source | Validation |
|---|---|---|
| Earthquake | USGS GeoJSON summary feed | Requires feature id, timestamp, valid point geometry, magnitude/depth sanity checks |
| Wildfire | NASA FIRMS Area API | Request bbox is India-only: `68,6,98,38`; validator rejects records outside India |
| Flood | Central Water Commission and configured state bulletins | Requires station/bulletin geometry inside India; un-geotagged rows are dropped |
| Cyclone | IMD/RSMC and JTWC | Parses HTML/text bulletins; requires North Indian Ocean geometry |
| Weather | Open-Meteo | Requires configured India points and non-negative rainfall values |

## Validation Rules

- All stored source records require a deterministic `source_event_id`.
- All persisted geospatial records must pass SRID 4326 latitude/longitude bounds.
- India-scoped feeds use the India bbox unless the hazard naturally occurs offshore, such as cyclones.
- Duplicate source records are removed before storage and guarded by unique database constraints.
- Raw source payloads are retained in JSONB for auditability.

## Source References

- USGS GeoJSON summary format: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
- NASA FIRMS Area API: https://firms.modaps.eosdis.nasa.gov/api/area/
- CWC Flood Forecast Dashboard: https://cwc.gov.in/ffm_dashboard
- IMD/RSMC New Delhi: https://rsmcnewdelhi.imd.gov.in/
- JTWC public warning page: https://www.metoc.navy.mil/jtwc/jtwc.html
- Open-Meteo forecast API: https://open-meteo.com/en/docs

