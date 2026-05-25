"""Train DamageSegmenter on synthetic 4-class damage data.

Phase-1 bootstrap: produces a working checkpoint at ml/models/damage_segmenter.pt
so /api/damage/segment can respond with real inference. Fine-tune on xView2
in Phase 2 (see ALERTIX_AI_DOCUMENTATION.md §6.7).

Run:
    python ml/scripts/train_damage_segmenter.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

import numpy as np

from app.ml.damage_segment import DAMAGE_CLASSES, DamageSegmenter


def synth_dataset(n_per_class: int = 32, size: int = 64, seed: int = 7):
    """Generate synthetic (image, label, mask) triples.

    Each class has a characteristic intensity + mask pattern so the small CNN
    can fit it reliably. Not realistic — only enough to load valid weights.
    """
    rng = np.random.default_rng(seed)
    images, labels, masks = [], [], []
    for cls_idx in range(len(DAMAGE_CLASSES)):
        for _ in range(n_per_class):
            base = rng.uniform(0.1 + 0.2 * cls_idx, 0.3 + 0.2 * cls_idx, (3, size, size))
            base = base.astype(np.float32)
            mask = np.zeros((size, size), dtype=np.float32)
            if cls_idx > 0:
                blob_h = rng.integers(8, size // 2)
                blob_w = rng.integers(8, size // 2)
                y0 = rng.integers(0, size - blob_h)
                x0 = rng.integers(0, size - blob_w)
                mask[y0 : y0 + blob_h, x0 : x0 + blob_w] = 1.0
                base[:, y0 : y0 + blob_h, x0 : x0 + blob_w] += 0.2 * cls_idx
            images.append(base)
            labels.append(cls_idx)
            masks.append(mask)
    return (
        np.stack(images).astype(np.float32),
        np.array(labels, dtype=np.int64),
        np.stack(masks).astype(np.float32),
    )


def main() -> None:
    print("Generating synthetic dataset...")
    X, y, M = synth_dataset()
    print(f"  shapes: X={X.shape}, y={y.shape}, M={M.shape}")

    print("Training DamageSegmenter (mini-batches, CPU)...")
    seg = DamageSegmenter()
    # Mini-batch training so the model learns all 4 classes
    rng = np.random.default_rng(11)
    n_epochs = 40
    batch_size = 16
    n = len(X)
    for epoch in range(n_epochs):
        idx = rng.permutation(n)
        for start in range(0, n, batch_size):
            sel = idx[start : start + batch_size]
            seg.train_model(X[sel], y[sel], M[sel], epochs=1, lr=2e-3)
        if (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch + 1}/{n_epochs}")
    # Final full-set metrics
    metrics = seg.train_model(X, y, M, epochs=1, lr=1e-4)
    print(f"  per-class accuracy: {metrics}")

    out = REPO / "ml" / "models" / "damage_segmenter.pt"
    out.parent.mkdir(parents=True, exist_ok=True)
    seg.save(out)
    print(f"Saved checkpoint to {out}")
    print(f"\nSet DAMAGE_MODEL_CHECKPOINT={out} in .env to enable /api/damage/segment")


if __name__ == "__main__":
    main()
