"""SOS text enrichment: regex NER + Nominatim geocoding.

Phase-1 approach. Phase 2 plan (per ALERTIX_AI_DOCUMENTATION.md §6.6):
upgrade to spaCy en_core_web_trf + custom Indian-place NER + self-hosted
Nominatim + GeoNames fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.logging import get_logger

log = get_logger(__name__)

# Common Indian place markers — used to filter regex candidates
_INDIA_HINTS = (
    " india",
    " delhi",
    " mumbai",
    " hyderabad",
    " chennai",
    " bengaluru",
    " bangalore",
    " kolkata",
    " ahmedabad",
    " jaipur",
    " telangana",
    " karnataka",
    " kerala",
    " tamil",
    " andhra",
    " maharashtra",
    " odisha",
    " bihar",
    " assam",
    " gujarat",
    " punjab",
    " uttar",
    " madhya",
    " west bengal",
    " rajasthan",
    " sikkim",
    " manipur",
    " meghalaya",
    " mizoram",
    " nagaland",
    " tripura",
    " arunachal",
)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True, slots=True)
class SosEnrichment:
    place_candidates: list[str]
    chosen_place: str | None
    latitude: float | None
    longitude: float | None
    provider: str  # "nominatim" | "none"


def extract_places(text: str) -> list[str]:
    """Pull plausible Indian place names. Naive: 1-3 capitalised words."""
    if not text:
        return []
    raw = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2}\b", text)
    # Dedupe preserving order
    seen: set[str] = set()
    out = []
    for name in raw:
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


async def geocode(place: str, country: str = "in") -> tuple[float, float] | None:
    """Geocode via public Nominatim. Respect the 1-req/sec ToS by callers."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                _NOMINATIM_URL,
                params={"q": place, "format": "json", "limit": 1, "countrycodes": country},
                headers={"User-Agent": "AlertixAI/0.1 (https://alertix.ai)"},
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            return (float(data[0]["lat"]), float(data[0]["lon"]))
    except Exception as exc:
        log.warning("nominatim_geocode_failed place=%s error=%s", place, exc)
        return None


async def enrich_sos(text: str) -> SosEnrichment:
    """Extract places from SOS text and geocode the most plausible one."""
    candidates = extract_places(text)
    if not candidates:
        return SosEnrichment([], None, None, None, "none")

    # Prefer a candidate that co-occurs with an Indian-context hint
    lowered = text.lower()
    ranked = sorted(
        candidates,
        key=lambda c: (
            not any(h in lowered for h in _INDIA_HINTS),  # India-hint candidates first
            -len(c),  # longer names rank higher
        ),
    )
    for cand in ranked[:3]:
        coords = await geocode(cand)
        if coords:
            return SosEnrichment(
                place_candidates=candidates,
                chosen_place=cand,
                latitude=coords[0],
                longitude=coords[1],
                provider="nominatim",
            )

    return SosEnrichment(candidates, ranked[0] if ranked else None, None, None, "none")
