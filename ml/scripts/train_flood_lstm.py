"""Train the FloodLSTM on synthetic Krishna-basin-like sequences.

Phase-1 bootstrap so /api/predict/flood and the flood tab can render a
real forecast. Replace with real 5-yr CWC + IMD basin data in Phase 2.

Run:
    python ml/scripts/train_flood_lstm.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from app.ml.flood_lstm import FloodLSTM


def synth_sequences(n: int = 2000, seed: int = 21):
    """Generate (X, y) where X is (7, 2) sequences and y is (3,) forecasts.

    Physics-inspired: river level at t+h is a function of current level,
    cumulative rainfall over the last week, and a lag term. Forecast horizons
    are 24h / 48h / 72h ahead.
    """
    rng = np.random.default_rng(seed)
    X, y = [], []
    for _ in range(n):
        # 7 days of rainfall (mm/day) — mix calm and monsoon-burst patterns
        regime = rng.choice(["calm", "monsoon", "storm"], p=[0.5, 0.35, 0.15])
        if regime == "calm":
            rain = rng.exponential(2.0, size=7)
        elif regime == "monsoon":
            rain = rng.normal(40, 15, size=7).clip(0, None)
        else:  # storm
            rain = rng.exponential(5, size=7)
            burst_day = rng.integers(0, 7)
            rain[burst_day] += rng.uniform(80, 200)

        # River level (m) — initial + cumulative response (1-day lag)
        base_level = rng.uniform(0.5, 2.5)
        levels = np.zeros(7, dtype=np.float32)
        levels[0] = base_level
        for d in range(1, 7):
            levels[d] = levels[d - 1] + 0.012 * rain[d - 1] - 0.05  # drainage
            levels[d] = max(0.1, levels[d])

        # Future forecasts (24h, 48h, 72h ahead) — same dynamics extended
        future_rain = np.full(3, rain[-3:].mean())  # assume persistence
        f24 = levels[-1] + 0.012 * rain[-1] - 0.05
        f48 = f24 + 0.012 * future_rain[0] - 0.05
        f72 = f48 + 0.012 * future_rain[1] - 0.05
        forecasts = np.array([max(0.1, f24), max(0.1, f48), max(0.1, f72)], dtype=np.float32)

        seq = np.stack([rain.astype(np.float32), levels], axis=1)  # (7, 2)
        X.append(seq)
        y.append(forecasts)
    return np.stack(X), np.stack(y)


def main() -> None:
    print("Generating synthetic Krishna-basin-like dataset...")
    X, y = synth_sequences(n=2000)
    # Train/val split
    split = int(len(X) * 0.8)
    X_tr, y_tr = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]
    print(f"  train={X_tr.shape}, val={X_val.shape}")

    print("Training FloodLSTM (mini-batch SGD, CPU)...")
    model = FloodLSTM()
    # Mini-batch training
    rng = np.random.default_rng(7)
    batch = 64
    for epoch in range(80):
        idx = rng.permutation(len(X_tr))
        for start in range(0, len(X_tr), batch):
            sel = idx[start : start + batch]
            model.train_model(X_tr[sel], y_tr[sel], X_val, y_val, epochs=1, lr=3e-3)
        if (epoch + 1) % 20 == 0:
            print(f"  epoch {epoch + 1}  rmse={model.metrics.get('rmse', 0):.3f}m  "
                  f"mae={model.metrics.get('mae', 0):.3f}m")

    out = REPO / "ml" / "models" / "flood_lstm.pt"
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(out)
    print(f"\nSaved checkpoint to {out}")
    print(f"Set FLOOD_LSTM_CHECKPOINT={out} in .env")


if __name__ == "__main__":
    main()
