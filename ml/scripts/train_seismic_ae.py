"""
Seismic LSTM Autoencoder -- Training Script
==========================================
Usage:
    python ml/scripts/train_seismic_ae.py \
        --catalog data/usgs_india_5yr.csv \
        --output models/seismic_ae.pt \
        --epochs 50 --batch-size 64

Data expected columns:
    time, latitude, longitude, depth, magnitude,
    rms, gap, horizontalError

The script:
1. Loads USGS catalog CSV
2. Builds 30-day rolling windows per 0.5-deg grid cell
3. Normalises with sklearn StandardScaler
4. Trains LSTM Autoencoder for anomaly detection
5. Saves weights + scaler to --output path
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


FEATURE_COLS = ["latitude", "longitude", "depth", "magnitude", "rms", "gap",
                "horizontalError", "count_30d"]
SEQ_LEN = 30


def load_catalog(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    df["count_30d"] = (
        df.set_index("time")["magnitude"]
        .rolling("30D")
        .count()
        .values
    )
    df[FEATURE_COLS] = df[FEATURE_COLS].fillna(0.0)
    return df


def make_sequences(df: pd.DataFrame, seq_len: int = SEQ_LEN) -> np.ndarray:
    data = df[FEATURE_COLS].values.astype(np.float32)
    seqs = []
    for i in range(len(data) - seq_len):
        seqs.append(data[i : i + seq_len])
    return np.array(seqs)


def train(
    catalog_path: Path,
    output_path: Path,
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 1e-3,
) -> None:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
        from sklearn.preprocessing import StandardScaler
        import pickle
    except ImportError as e:
        log.error("Missing deps: %s. Install with: pip install torch scikit-learn", e)
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parents[2] / "backend"))
    from app.ml.seismic_model import SeismicAutoencoder

    log.info("Loading catalog from %s", catalog_path)
    df = load_catalog(catalog_path)
    log.info("Catalog loaded: %d events", len(df))

    seqs = make_sequences(df)
    log.info("Sequences: %s", seqs.shape)

    flat = seqs.reshape(-1, seqs.shape[-1])
    scaler = StandardScaler().fit(flat)
    seqs_scaled = scaler.transform(flat).reshape(seqs.shape).astype(np.float32)

    tensor = torch.tensor(seqs_scaled)
    loader = DataLoader(TensorDataset(tensor), batch_size=batch_size, shuffle=True)

    model = SeismicAutoencoder(input_size=len(FEATURE_COLS), seq_len=SEQ_LEN)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for (batch,) in loader:
            opt.zero_grad()
            recon = model(batch)
            loss = criterion(recon, batch)
            loss.backward()
            opt.step()
            total_loss += loss.item() * len(batch)
        avg = total_loss / len(tensor)
        if epoch % 10 == 0 or epoch == 1:
            log.info("Epoch %d/%d  loss=%.6f", epoch, epochs, avg)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
    with open(output_path.with_suffix(".scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)
    log.info("Model saved to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("models/seismic_ae.pt"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    train(args.catalog, args.output, args.epochs, args.batch_size)
