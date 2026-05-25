"""Train FloodUNet on synthetic SAR-style flood extent data.

Phase-2 bootstrap: produces a working checkpoint at ml/models/flood_unet.pt
so the inference shim has weights to load. Fine-tune on Sentinel-1 GRD scenes
+ official flood masks (see ALERTIX_AI_DOCUMENTATION.md §6.2).

Each synthetic sample is a 4-channel image (VV, VH, NDWI, slope) at 64x64
with a flooded-region mask. Water reflects radar weakly so flooded pixels
are low VV/VH and high NDWI.

Run:
    python ml/scripts/train_flood_unet.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

import numpy as np

from app.ml.flood_unet import FloodUNet


def synth_dataset(n: int = 64, size: int = 64, seed: int = 17):
    rng = np.random.default_rng(seed)
    X = rng.uniform(0.3, 0.8, (n, 4, size, size)).astype(np.float32)
    y = np.zeros((n, size, size), dtype=np.float32)
    for i in range(n):
        n_blobs = rng.integers(1, 4)
        for _ in range(n_blobs):
            h = int(rng.integers(8, size // 2))
            w = int(rng.integers(8, size // 2))
            y0 = int(rng.integers(0, size - h))
            x0 = int(rng.integers(0, size - w))
            y[i, y0 : y0 + h, x0 : x0 + w] = 1.0
            X[i, 0, y0 : y0 + h, x0 : x0 + w] = rng.uniform(0.0, 0.15)  # VV low
            X[i, 1, y0 : y0 + h, x0 : x0 + w] = rng.uniform(0.0, 0.15)  # VH low
            X[i, 2, y0 : y0 + h, x0 : x0 + w] = rng.uniform(0.7, 1.0)   # NDWI high
            X[i, 3, y0 : y0 + h, x0 : x0 + w] = rng.uniform(0.0, 0.1)   # slope low
    return X, y


def main() -> None:
    print("Generating synthetic SAR flood dataset...")
    X, y = synth_dataset()
    print(f"  shapes: X={X.shape}, y={y.shape}")

    print("Training FloodUNet (CPU, 40 epochs)...")
    unet = FloodUNet(in_channels=4)
    rng = np.random.default_rng(23)
    batch = 8
    for epoch in range(40):
        idx = rng.permutation(len(X))
        for start in range(0, len(X), batch):
            sel = idx[start : start + batch]
            unet.train_model(X[sel], y[sel], epochs=1, lr=2e-3)
        if (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch + 1}/40")

    final = unet.train_model(X, y, epochs=1, lr=1e-4)
    print(f"  final IoU={final['iou']:.3f} F1={final['f1']:.3f}")

    out = REPO / "ml" / "models" / "flood_unet.pt"
    out.parent.mkdir(parents=True, exist_ok=True)
    unet.save(out)
    print(f"Saved checkpoint to {out}")
    print(f"\nSet FLOOD_UNET_CHECKPOINT={out} in .env to load this model.")


if __name__ == "__main__":
    main()
