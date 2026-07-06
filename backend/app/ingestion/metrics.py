"""In-process ingestion metrics for Prometheus exposition."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class IngestMetric:
    fetched: int = 0
    parsed: int = 0
    valid: int = 0
    malformed: int = 0
    duplicates: int = 0
    stored: int = 0
    streamed: int = 0
    schema_drift: int = 0
    last_seen_epoch: float = field(default_factory=time.time)


class IngestionMetrics:
    def __init__(self) -> None:
        self._metrics: defaultdict[str, IngestMetric] = defaultdict(IngestMetric)

    def record(
        self,
        source: str,
        *,
        fetched: int = 0,
        parsed: int = 0,
        valid: int = 0,
        malformed: int = 0,
        duplicates: int = 0,
        stored: int = 0,
        streamed: int = 0,
        schema_drift: int = 0,
    ) -> None:
        m = self._metrics[source]
        m.fetched += fetched
        m.parsed += parsed
        m.valid += valid
        m.malformed += malformed
        m.duplicates += duplicates
        m.stored += stored
        m.streamed += streamed
        m.schema_drift += schema_drift
        m.last_seen_epoch = time.time()

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        return {
            name: {
                "fetched": metric.fetched,
                "parsed": metric.parsed,
                "valid": metric.valid,
                "malformed": metric.malformed,
                "duplicates": metric.duplicates,
                "stored": metric.stored,
                "streamed": metric.streamed,
                "schema_drift": metric.schema_drift,
                "last_seen_epoch": round(metric.last_seen_epoch, 3),
            }
            for name, metric in sorted(self._metrics.items())
        }

    def prometheus_text(self) -> str:
        lines: list[str] = []
        for source, metric in sorted(self._metrics.items()):
            labels = f'source="{source}"'
            lines.extend(
                [
                    f"alertix_ingest_fetched_total{{{labels}}} {metric.fetched}",
                    f"alertix_ingest_parsed_total{{{labels}}} {metric.parsed}",
                    f"alertix_ingest_valid_total{{{labels}}} {metric.valid}",
                    f"alertix_ingest_malformed_total{{{labels}}} {metric.malformed}",
                    f"alertix_ingest_duplicates_total{{{labels}}} {metric.duplicates}",
                    f"alertix_ingest_stored_total{{{labels}}} {metric.stored}",
                    f"alertix_ingest_streamed_total{{{labels}}} {metric.streamed}",
                    f"alertix_ingest_schema_drift_total{{{labels}}} {metric.schema_drift}",
                ]
            )
        return "\n".join(lines) + "\n"


metrics = IngestionMetrics()
