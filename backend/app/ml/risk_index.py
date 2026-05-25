"""Composite Alertix Risk Index — XGBoost over per-region hazard features.

Takes 7 features per region/point and returns a 0-1 risk index that fuses
earthquake, flood, cyclone, wildfire, landslide signals. Trained on
synthetic-but-physics-consistent labels in ml/scripts/train_risk_index.py.

Features (must match training order):
    0  eq_count_30d            recent earthquake count in radius
    1  eq_max_magnitude        largest mag in radius (last 30d)
    2  flood_max_intensity     max river severity (0-1)
    3  rainfall_72h_mm         72h cumulative rainfall
    4  wildfire_count_24h      FIRMS hotspots in radius (last 24h)
    5  cyclone_wind_kmh        nearest active cyclone wind speed
    6  landslide_rule_score    GSI-zone + rainfall rule score (0-1)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)

FEATURE_NAMES = (
    "eq_count_30d",
    "eq_max_magnitude",
    "flood_max_intensity",
    "rainfall_72h_mm",
    "wildfire_count_24h",
    "cyclone_wind_kmh",
    "landslide_rule_score",
)

_MODEL_CACHE: Any = None


def _weights_path() -> Path:
    from app.config import get_settings

    settings = get_settings()
    override = getattr(settings, "risk_index_checkpoint", "") or ""
    if override:
        return Path(override)
    return Path(settings.model_weights_dir) / "risk_index.json"


def _load_model() -> Any:
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    path = _weights_path()
    if not path.exists():
        log.info("risk_index_weights_not_found path=%s", path)
        return None
    try:
        import xgboost as xgb

        booster = xgb.Booster()
        booster.load_model(str(path))
        _MODEL_CACHE = booster
        log.info("risk_index_loaded path=%s", path)
        return booster
    except Exception as exc:
        log.warning("risk_index_load_failed: %s", exc)
        return None


def score(features: dict[str, float] | list[float]) -> float:
    """Return composite risk in [0, 1]. -1.0 if model unavailable."""
    booster = _load_model()
    if booster is None:
        return -1.0
    if isinstance(features, dict):
        arr = np.array([[features.get(n, 0.0) for n in FEATURE_NAMES]], dtype=np.float32)
    else:
        arr = np.array([features], dtype=np.float32)
    try:
        import xgboost as xgb

        dmat = xgb.DMatrix(arr, feature_names=list(FEATURE_NAMES))
        pred = booster.predict(dmat)
        return float(np.clip(pred[0], 0.0, 1.0))
    except Exception as exc:
        log.warning("risk_index_inference_failed: %s", exc)
        return -1.0
