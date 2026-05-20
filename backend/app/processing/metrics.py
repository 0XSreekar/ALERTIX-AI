"""Small in-process metrics registry for processing workers."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class ConsumerMetric:
    processed: int = 0
    failed: int = 0
    dlq: int = 0
    duplicate: int = 0
    total_latency_ms: float = 0.0
    last_seen_epoch: float = field(default_factory=time.time)

    @property
    def avg_latency_ms(self) -> float:
        if self.processed <= 0:
            return 0.0
        return self.total_latency_ms / self.processed


class ProcessingMetrics:
    def __init__(self) -> None:
        self._metrics: defaultdict[str, ConsumerMetric] = defaultdict(ConsumerMetric)

    def record_success(self, consumer: str, latency_ms: float) -> None:
        metric = self._metrics[consumer]
        metric.processed += 1
        metric.total_latency_ms += latency_ms
        metric.last_seen_epoch = time.time()

    def record_failure(self, consumer: str) -> None:
        metric = self._metrics[consumer]
        metric.failed += 1
        metric.last_seen_epoch = time.time()

    def record_dlq(self, consumer: str) -> None:
        metric = self._metrics[consumer]
        metric.dlq += 1
        metric.last_seen_epoch = time.time()

    def record_duplicate(self, consumer: str) -> None:
        metric = self._metrics[consumer]
        metric.duplicate += 1
        metric.last_seen_epoch = time.time()

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        return {
            name: {
                "processed": metric.processed,
                "failed": metric.failed,
                "dlq": metric.dlq,
                "duplicate": metric.duplicate,
                "avg_latency_ms": round(metric.avg_latency_ms, 3),
                "last_seen_epoch": round(metric.last_seen_epoch, 3),
            }
            for name, metric in sorted(self._metrics.items())
        }

    def prometheus_text(self) -> str:
        lines: list[str] = []
        for consumer, metric in sorted(self._metrics.items()):
            labels = f'consumer="{consumer}"'
            lines.extend(
                [
                    f"alertix_processing_processed_total{{{labels}}} {metric.processed}",
                    f"alertix_processing_failed_total{{{labels}}} {metric.failed}",
                    f"alertix_processing_dlq_total{{{labels}}} {metric.dlq}",
                    f"alertix_processing_duplicate_total{{{labels}}} {metric.duplicate}",
                    f"alertix_processing_avg_latency_ms{{{labels}}} {metric.avg_latency_ms:.3f}",
                ]
            )
        return "\n".join(lines) + "\n"


metrics = ProcessingMetrics()
