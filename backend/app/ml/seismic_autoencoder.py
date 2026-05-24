"""Seismic LSTM autoencoder -- inference wrapper.

Training happens in ml/notebooks/seismic_autoencoder.ipynb.
This module loads the trained weights from R2 and scores new events.
If weights are not available it returns a sentinel score of -1.0.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import numpy as np

log = logging.getLogger(__name__)

_MODEL_CACHE: object | None = None


def _resolve_weights_path() -> Path:
    """Resolve checkpoint path from settings, falling back to legacy /tmp location."""
    from app.config import get_settings

    settings = get_settings()
    if settings.seismic_ae_checkpoint:
        return Path(settings.seismic_ae_checkpoint)
    # Legacy default — used in Linux containers
    return Path("/tmp/seismic_ae.pt")


def _try_load_model() -> object | None:
    """Load torch model if weights exist, else return None."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    weights_path = _resolve_weights_path()
    if not weights_path.exists():
        log.info("seismic_ae_weights_not_found path=%s", weights_path)
        return None
    try:
        import torch

        from app.ml.seismic_model import SeismicAutoencoder

        model = SeismicAutoencoder()
        model.load_state_dict(torch.load(weights_path, map_location="cpu"))
        model.eval()
        _MODEL_CACHE = model
        log.info("seismic_ae_loaded path=%s", weights_path)
        return model
    except Exception as exc:
        log.warning("seismic_ae_load_failed: %s", exc)
        return None


def score_event(features: list[float] | list[list[float]]) -> float:
    """Return reconstruction MSE (anomaly score). -1.0 = model unavailable.

    Accepts either:
      - A single 8-dim feature vector (will be tiled across the 30-step window)
      - A full (30, 8) sequence of features
    """
    model = cast(Any, _try_load_model())
    if model is None:
        return -1.0
    try:
        import torch

        arr = np.asarray(features, dtype=np.float32)
        if arr.ndim == 1:
            arr = np.tile(arr[None, :], (30, 1))
        elif arr.ndim != 2:
            log.warning("seismic_ae invalid input ndim=%d", arr.ndim)
            return -1.0
        x = torch.tensor(arr[None, :, :], dtype=torch.float32)  # (1, seq_len, input_size)
        with torch.no_grad():
            recon = model(x)
        mse = float(torch.mean((recon - x) ** 2).item())
        return mse
    except Exception as exc:
        log.warning("seismic_ae_inference_failed: %s", exc)
        return -1.0


def omori_aftershock_probability(
    mainshock_mag: float,
    hours_since: float,
    p: float = 1.1,
    c: float = 0.05,
    k: float = 10.0,
) -> float:
    """Omori-Utsu decay: rate = K / (t + c)^p. Returns prob in [0,1] via sigmoid."""
    if hours_since < 0:
        hours_since = 0.0
    rate = k * (mainshock_mag / 6.0) / ((hours_since + c) ** p)
    # Sigmoid to squash to probability
    prob = 1.0 / (1.0 + np.exp(-rate + 3.0))
    return float(np.clip(prob, 0.0, 1.0))
