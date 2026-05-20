"""Stress harness for 1000 concurrent synthetic stream events.

Run against a local stack with:
    python tests/stress/pipeline_stress.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from redis.asyncio import from_url

STREAM = "hazard:events"


async def main() -> None:
    redis = from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    started = datetime.now(UTC)

    async def publish(i: int) -> None:
        await redis.xadd(
            STREAM,
            {
                "event_id": f"00000000-0000-0000-0000-{i:012d}",
                "source": "stress",
                "hazard_type": "earthquake",
                "timestamp": started.isoformat(),
                "latitude": str(16.0 + (i % 100) / 100),
                "longitude": "80.0",
                "magnitude": str(4.0 + (i % 40) / 10),
                "depth": "12",
                "confidence": "1",
                "raw_payload": json.dumps({"stress_index": i}),
            },
        )

    await asyncio.gather(*(publish(i) for i in range(1000)))
    await redis.aclose()
    elapsed = (datetime.now(UTC) - started).total_seconds()
    print(json.dumps({"events": 1000, "publish_seconds": elapsed, "events_per_second": 1000 / elapsed}))


if __name__ == "__main__":
    asyncio.run(main())
