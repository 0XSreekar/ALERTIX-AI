"""
Flood LSTM Training Script
==========================
Usage:
    python ml/scripts/train_flood_lstm.py \
        --data data/cwc_gauges.csv \
        --output models/flood_lstm.pt \
        --epochs 25 --basin krishna

Data CSV expected columns:
    datetime, rainfall_mm, river_level_m, gauge_id, basin

The script:
1. Loads CWC gauge + rainfall CSV
2. Builds 7-day sliding windows (input: [rainfall_mm, river_level_m])
3. Normalises with MinMaxScaler
4. Trains 2-layer LSTM for 24/48/72h discharge forecasting
5. Saves weights + scaler to --output path

Synthetic data mode (no CSV):
    python ml/scripts/train_flood_lstm.py --synthetic --output models/flood_lstm.pt
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

WINDOW_DAYS = 7
FEATURES = 2  # rainfall_mm, river_level_m
FORECAST_STEPS = 3  # 24h, 48h, 72h


def generate_synthetic(n_samples: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic seasonal gauge + rainfall data for smoke-test training."""
    t = np.linspace(0, 8 * np.pi, n_samples)
    rainfall = np.clip(2 * np.sin(t) + np.random.randn(n_samples) * 0.5 + 1, 0, None)
    level = np.clip(0.5 * np.cumsum(rainfall * 0.01) % 5 + np.random.randn(n_samples) * 0.1, 0, 10)
    return rainfall.astype(np.float32), level.astype(np.float32)


def load_csv(path: Path, basin: str | None) -> tuple[np.ndarray, np.ndarray]:
    try:
        import pandas as pd
    except ImportError:
        log.error("Install pandas: pip install pandas")
        sys.exit(1)

    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime")
    if basin:
        df = df[df["basin"].str.lower() == basin.lower()]
    if df.empty:
        log.error("No rows found for basin=%s", basin)
        sys.exit(1)
    df[["rainfall_mm", "river_level_m"]] = df[["rainfall_mm", "river_level_m"]].fillna(0.0)
    return df["rainfall_mm"].values.astype(np.float32), df["river_level_m"].values.astype(np.float32)


def make_windows(
    rainfall: np.ndarray, level: np.ndarray, window: int = WINDOW_DAYS * 24
) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(len(level) - window - FORECAST_STEPS):
        X.append(np.stack([rainfall[i : i + window], level[i : i + window]], axis=1))
        y.append(level[i + window : i + window + FORECAST_STEPS])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train(
    output_path: Path,
    data_path: Path | None = None,
    basin: str | None = None,
    epochs: int = 25,
    synthetic: bool = False,
) -> None:
    try:
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            raise ImportError("torch")
        from sklearn.preprocessing import MinMaxScaler
        import pickle
    except ImportError as e:
        log.error("Missing deps: %s. pip install torch scikit-learn", e)
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parents[2] / "backend"))
    from app.ml.flood_lstm import FloodLSTM

    if synthetic or data_path is None:
        log.info("Using synthetic data (no CSV provided)")
        rainfall, level = generate_synthetic(3000)
    else:
        log.info("Loading CSV from %s (basin=%s)", data_path, basin)
        rainfall, level = load_csv(data_path, basin)

    log.info("Series length: %d", len(level))

    scaler_r = MinMaxScaler()
    scaler_l = MinMaxScaler()
    rainfall_n = scaler_r.fit_transform(rainfall.reshape(-1, 1)).flatten()
    level_n = scaler_l.fit_transform(level.reshape(-1, 1)).flatten()

    # Use hourly steps; if daily data, window = 7 steps
    window = min(WINDOW_DAYS * 24, len(level) // 4)
    X, y = make_windows(rainfall_n, level_n, window)
    log.info("Windows: X=%s y=%s", X.shape, y.shape)

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    model = FloodLSTM(input_size=FEATURES, hidden_size=48)
    metrics = model.train_model(X_train, y_train, X_val, y_val, epochs=epochs)
    log.info("Training complete: RMSE=%.4f MAE=%.4f", metrics["rmse"], metrics["mae"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(output_path)

    scaler_path = output_path.with_suffix(".scalers.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump({"rainfall": scaler_r, "level": scaler_l}, f)

    log.info("Saved model → %s", output_path)
    log.info("Saved scalers → %s", scaler_path)
    log.info(
        "Set env: FLOOD_LSTM_CHECKPOINT=%s",
        output_path.resolve(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=None, help="CWC gauge CSV path")
    parser.add_argument("--output", type=Path, default=Path("models/flood_lstm.pt"))
    parser.add_argument("--basin", type=str, default=None, help="Filter by basin name")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data for testing")
    args = parser.parse_args()
    train(
        output_path=args.output,
        data_path=args.data,
        basin=args.basin,
        epochs=args.epochs,
        synthetic=args.synthetic or args.data is None,
    )
