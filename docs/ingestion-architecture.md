# Alertix AI Ingestion Architecture

## Scope

Phase 1 ingestion is a real-time data foundation only. It fetches trusted live feeds, validates records, stores normalized events in PostgreSQL/PostGIS, and publishes every accepted event to Redis stream `hazard:events`.

It does not run prediction models, LLM explanations, dashboard logic, or mocked source responses.

## Package Layout

```text
backend/app/ingestion/
  common/      shared retry, validation, dedupe, cache, storage, stream logging
  earthquake/  USGS GeoJSON feed
  wildfire/    NASA FIRMS India-bounded area API
  flood/       CWC gauges and configured official state bulletins
  cyclone/     IMD/RSMC and JTWC bulletin pages
  weather/     Open-Meteo rainfall feed
  workers/     scheduled job wrappers
```

Each hazard package has `client.py`, `parser.py`, `validator.py`, and `service.py`.

## Data Lifecycle

1. Client fetches source data with async HTTP, timeout handling, retries, and short TTL caching where appropriate.
2. Parser converts raw payloads into `NormalizedEvent`.
3. Validator rejects malformed geometry, invalid ranges, duplicates, and out-of-scope records.
4. Storage bulk-upserts into `hazard_events` plus the source table.
5. Legacy `events` is updated for existing dashboard/API compatibility where applicable.
6. Redis publisher sends accepted records to `hazard:events`.

## Redis Stream Contract

Stream: `hazard:events`

Fields include:

```json
{
  "id": "hazard_events UUID",
  "event_id": "same UUID for compatibility",
  "source": "usgs | nasa_firms_* | cwc | imd_rsmc | jtwc | open_meteo",
  "hazard_type": "earthquake | wildfire | flood | cyclone | weather",
  "timestamp": "UTC ISO-8601",
  "latitude": "number as string",
  "longitude": "number as string",
  "magnitude": "number as string or empty",
  "depth": "number as string or empty",
  "confidence": "0..1 as string or empty",
  "processing_state": "ingested",
  "retry_count": "integer string",
  "raw_payload": "source JSON string"
}
```

Redis failures are logged and do not roll back committed database writes.

## Database Strategy

`hazard_events` is the normalized lifecycle table. Source-specific tables store query-friendly fields:

- `earthquakes`
- `wildfires`
- `river_gauges`
- `cyclones`
- `weather_events`

All geo columns are PostGIS `GEOGRAPHY(Point, 4326)`. Source tables have unique source IDs and time/location indexes. Writes use JSONB recordset bulk upserts instead of row-by-row inserts.

## Source Services

- Earthquake: USGS GeoJSON summary feeds.
- Wildfire: NASA FIRMS Area API scoped to India bbox `68,6,98,38`.
- Flood: CWC flood dashboard/gauge tables and configured official state bulletin URLs.
- Cyclone: IMD/RSMC HTML bulletins plus JTWC public text products.
- Weather: Open-Meteo hourly rainfall for configured India points.

## Retry And Failure Handling

- HTTP requests use `httpx.AsyncClient` with connect/read timeouts.
- Transient HTTP/timeouts retry with exponential backoff and jitter.
- Malformed rows are dropped with structured logs.
- Duplicates are removed before DB writes and also protected by DB unique constraints.
- API downtime raises the ingestion job failure cleanly so cron/worker monitoring can alert.

## Scaling Notes

- FIRMS records are processed in batches to avoid memory-heavy one-row inserts.
- Future workers can consume `hazard:events` with Redis consumer groups.
- New source integrations should only add a source package and reuse common storage/stream utilities.
- CWC/state bulletin parsing deliberately stores only geotagged rows; records without trustworthy coordinates are logged as dropped rather than guessed.

