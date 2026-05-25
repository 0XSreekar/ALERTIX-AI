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


def _weights_path() -> Path:
    """Resolve weights path from settings (SEISMIC_AE_CHECKPOINT) or default."""
    from app.config import get_settings

    settings = get_settings()
    override = getattr(settings, "seismic_ae_checkpoint", "") or ""
    if override:
        return Path(override)
    # Fall back to model_weights_dir/seismic_ae.pt
    return Path(settings.model_weights_dir) / "seismic_ae.pt"


_WEIGHTS_PATH = _weights_path()


def _try_load_model() -> object | None:
    """Load torch model if weights exist, else return None."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    path = _weights_path()
    if not path.exists():
        log.info("seismic_ae_weights_not_found path=%s", path)
        return None
    try:
        import torch

        from app.ml.seismic_model import SeismicAutoencoder

        model = SeismicAutoencoder()
        model.load_state_dict(torch.load(path, map_location="cpu"))
        model.eval()
        _MODEL_CACHE = model
        log.info("seismic_ae_loaded path=%s", path)
        return model
    except Exception as exc:
        log.warning("seismic_ae_load_failed: %s", exc)
        return None


def score_event(features: list[float]) -> float:
    """Return reconstruction error (anomaly score). -1.0 = model unavailable."""
    model = cast(Any, _try_load_model())
    if model is None:
        return -1.0
    try:
        import torch

        x = torch.tensor([features], dtype=torch.float32)
        with torch.no_grad():
            recon = model(x)
        mse = float(torch.mean((recon - x) ** 2).item())
        return mse
    except Exception as exc:
        log.warning("seismic_ae_inference_failed: %s", exc)
        return -1.0


def score_sequence(sequence: list[list[float]]) -> float:
    """Score a 30-step seismic feature sequence. Returns reconstruction MSE,
    normalised by a baseline so the value is roughly in [0,1] for typical input.

    Sequence shape: (30, 8) — 8 features per step (lat, lon, depth, mag, rms,
    gap, horizontalError, count_30d). -1.0 = model unavailable.
    """
    model = cast(Any, _try_load_model())
    if model is None:
        return -1.0
    try:
        import numpy as np
        import torch

        arr = np.asarray(sequence, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] != 8:
            log.warning("score_sequence_bad_shape shape=%s expected=(N,8)", arr.shape)
            return -1.0
        if arr.shape[0] < 30:
            pad = np.zeros((30 - arr.shape[0], 8), dtype=np.float32)
            arr = np.vstack([pad, arr])
        elif arr.shape[0] > 30:
            arr = arr[-30:]
        x = torch.tensor(arr[None, :, :], dtype=torch.float32)
        with torch.no_grad():
            recon = model(x)
        mse = float(torch.mean((recon - x) ** 2).item())
        # Squash to [0,1]; typical training MSE was ~0.75
        return float(min(1.0, max(0.0, mse / 1.5)))
    except Exception as exc:
        log.warning("seismic_ae_sequence_inference_failed: %s", exc)
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
