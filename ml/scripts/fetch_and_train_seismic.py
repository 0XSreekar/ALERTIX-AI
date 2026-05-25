"""Download 5-yr USGS India catalog and train the seismic LSTM autoencoder.

USGS FDSN limits each request to 20k events, so we paginate by year.

Run:
    python ml/scripts/fetch_and_train_seismic.py
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ml" / "scripts"))
sys.path.insert(0, str(REPO / "backend"))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# India + plate-boundary bounding box (approx)
BBOX = dict(minlatitude=4, maxlatitude=40, minlongitude=66, maxlongitude=100)
YEARS_BACK = 5
MIN_MAG = 2.5  # filter noise; ~30k events over 5yrs


def fetch_year(start: datetime, end: datetime) -> pd.DataFrame:
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "csv",
        "starttime": start.strftime("%Y-%m-%d"),
        "endtime": end.strftime("%Y-%m-%d"),
        "minmagnitude": MIN_MAG,
        **BBOX,
    }
    log.info("fetching %s -> %s", params["starttime"], params["endtime"])
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    from io import StringIO

    return pd.read_csv(StringIO(r.text))


def main() -> None:
    out_csv = REPO / "ml" / "data" / "usgs_india_5yr.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if out_csv.exists():
        log.info("catalog already cached at %s", out_csv)
    else:
        end = datetime.now(timezone.utc)
        chunks = []
        for i in range(YEARS_BACK):
            chunk_end = end - timedelta(days=365 * i)
            chunk_start = end - timedelta(days=365 * (i + 1))
            try:
                df = fetch_year(chunk_start, chunk_end)
                chunks.append(df)
            except Exception as exc:
                log.warning("year %d fetch failed: %s", i, exc)
        if not chunks:
            log.error("no data fetched")
            sys.exit(1)
        combined = pd.concat(chunks, ignore_index=True)
        combined.to_csv(out_csv, index=False)
        log.info("saved %d events to %s", len(combined), out_csv)

    # USGS CSV columns include: time, latitude, longitude, depth, mag, rms, gap, horizontalError
    # The training script expects 'magnitude' not 'mag'. Normalize columns.
    df = pd.read_csv(out_csv)
    if "magnitude" not in df.columns and "mag" in df.columns:
        df = df.rename(columns={"mag": "magnitude"})
    # Make sure required columns exist; fill missing with 0
    for col in ("rms", "gap", "horizontalError"):
        if col not in df.columns:
            df[col] = 0.0
    df = df.dropna(subset=["time", "latitude", "longitude", "magnitude"])
    normalized_csv = REPO / "ml" / "data" / "usgs_india_5yr_normalized.csv"
    df.to_csv(normalized_csv, index=False)
    log.info("normalized catalog: %d events -> %s", len(df), normalized_csv)

    # Train
    from train_seismic_ae import train

    weights = REPO / "ml" / "models" / "seismic_ae.pt"
    train(normalized_csv, weights, epochs=20, batch_size=64)
    log.info("done. weights at %s", weights)


if __name__ == "__main__":
    main()
