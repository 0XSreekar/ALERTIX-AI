"""Train the composite Alertix Risk Index XGBoost model on synthetic data.

Labels are produced by a physics-inspired rule that weights each hazard,
so the model learns a smooth, monotonic fusion. Replace with real
historical disaster impact data in Phase 2.

Run:
    python ml/scripts/train_risk_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xgboost as xgb

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from app.ml.risk_index import FEATURE_NAMES


def synth_dataset(n: int = 8000, seed: int = 31):
    """Generate (X, y) — features and 0-1 risk labels.

    Sampling spans realistic ranges for each feature; label is a weighted
    sigmoid so XGBoost learns a sensible fusion.
    """
    rng = np.random.default_rng(seed)
    eq_count = rng.gamma(2.0, 4.0, size=n).clip(0, 60)
    eq_max_mag = rng.uniform(0, 7.5, size=n)
    flood_int = rng.beta(2, 6, size=n)
    rain_72h = rng.exponential(40, size=n).clip(0, 500)
    fire_count = rng.gamma(1.5, 6, size=n).clip(0, 200)
    cyc_wind = np.where(rng.uniform(size=n) < 0.15, rng.uniform(60, 250, size=n), 0.0)
    landslide = rng.beta(2, 4, size=n)

    X = np.column_stack(
        [eq_count, eq_max_mag, flood_int, rain_72h, fire_count, cyc_wind, landslide]
    ).astype(np.float32)

    # Weighted risk score with thresholds matching domain intuition
    raw = (
        0.10 * (eq_count / 60)
        + 0.20 * (eq_max_mag / 7.5)
        + 0.15 * flood_int
        + 0.15 * (rain_72h / 250).clip(0, 1)
        + 0.10 * (fire_count / 80).clip(0, 1)
        + 0.20 * (cyc_wind / 200).clip(0, 1)
        + 0.10 * landslide
    )
    # Smooth sigmoid + a little noise
    y = 1.0 / (1.0 + np.exp(-(raw - 0.45) * 6.0))
    y += rng.normal(0, 0.03, size=n)
    y = y.clip(0.0, 1.0).astype(np.float32)
    return X, y


def main() -> None:
    print("Generating synthetic dataset (8000 samples, 7 features)...")
    X, y = synth_dataset()
    split = int(0.85 * len(X))
    X_tr, y_tr = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]
    print(f"  train={X_tr.shape}, val={X_val.shape}")

    dtrain = xgb.DMatrix(X_tr, label=y_tr, feature_names=list(FEATURE_NAMES))
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=list(FEATURE_NAMES))

    params = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "eta": 0.08,
        "max_depth": 5,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "verbosity": 1,
    }
    print("Training XGBoost...")
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=400,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=20,
        verbose_eval=50,
    )

    out = REPO / "ml" / "models" / "risk_index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(out))
    print(f"\nSaved model to {out}")
    print(f"Set RISK_INDEX_CHECKPOINT={out} in .env")


if __name__ == "__main__":
    main()
