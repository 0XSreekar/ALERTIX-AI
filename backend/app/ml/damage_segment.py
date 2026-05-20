"""Damage classifier and segmentation head for citizen imagery."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)

DAMAGE_CLASSES = ("no_damage", "minor", "major", "destroyed")


def _torch() -> Any:
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("Install alertix-backend[ml] to use DamageSegmenter") from exc
    return torch, nn


@dataclass(frozen=True, slots=True)
class DamagePrediction:
    class_label: str
    confidence: float
    bounding_boxes: list[dict[str, float | str]]
    latency_ms: float


class DamageSegmenter:
    def __init__(self, checkpoint: str | Path | None = None) -> None:
        torch, nn = _torch()

        class _Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 24, 3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(2),
                    nn.Conv2d(24, 48, 3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(2),
                    nn.Conv2d(48, 96, 3, padding=1),
                    nn.ReLU(inplace=True),
                )
                self.classifier = nn.Sequential(
                    nn.AdaptiveAvgPool2d(1),
                    nn.Flatten(),
                    nn.Linear(96, len(DAMAGE_CLASSES)),
                )
                self.mask_head = nn.Conv2d(96, 1, kernel_size=1)

            def forward(self, x):  # type: ignore[no-untyped-def]
                feat = self.features(x)
                return self.classifier(feat), self.mask_head(feat)

        self.torch = torch
        self.model = _Model()
        self.loaded = False
        self.metrics: dict[str, float] = {}
        if checkpoint:
            self.load(checkpoint)

    @staticmethod
    def per_class_accuracy(pred: np.ndarray, target: np.ndarray) -> dict[str, float]:
        metrics: dict[str, float] = {}
        for idx, label in enumerate(DAMAGE_CLASSES):
            selector = target == idx
            metrics[label] = float((pred[selector] == idx).mean()) if selector.any() else 0.0
        return metrics

    def train_model(
        self,
        images: np.ndarray,
        labels: np.ndarray,
        masks: np.ndarray,
        *,
        epochs: int = 10,
        lr: float = 1e-3,
    ) -> dict[str, float]:
        torch = self.torch
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        class_loss = torch.nn.CrossEntropyLoss()
        mask_loss = torch.nn.BCEWithLogitsLoss()
        x = torch.tensor(images, dtype=torch.float32)
        y = torch.tensor(labels, dtype=torch.long)
        m = torch.tensor(masks, dtype=torch.float32)
        if m.ndim == 3:
            m = m[:, None, :, :]
        for _ in range(max(1, epochs)):
            optimizer.zero_grad()
            logits, mask_logits = self.model(x)
            resized_masks = torch.nn.functional.interpolate(m, size=mask_logits.shape[-2:])
            loss = class_loss(logits, y) + mask_loss(mask_logits, resized_masks)
            loss.backward()
            optimizer.step()
        self.model.eval()
        with torch.no_grad():
            logits, _ = self.model(x)
            pred = torch.argmax(logits, dim=1).cpu().numpy()
        per_class = self.per_class_accuracy(pred, labels)
        self.metrics = {f"accuracy_{k}": v for k, v in per_class.items()}
        self.loaded = True
        return self.metrics

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.torch.save({"state_dict": self.model.state_dict(), "metrics": self.metrics}, path)

    def load(self, path: str | Path) -> None:
        checkpoint = self.torch.load(Path(path), map_location="cpu")
        self.model.load_state_dict(checkpoint["state_dict"])
        self.metrics = dict(checkpoint.get("metrics") or {})
        self.model.eval()
        self.loaded = True

    def predict(self, image: np.ndarray) -> DamagePrediction:
        if not self.loaded:
            raise RuntimeError("DamageSegmenter checkpoint is not loaded")
        arr = np.asarray(image, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[0] != 3:
            raise ValueError("image must have shape (3, height, width)")
        started = time.perf_counter()
        with self.torch.no_grad():
            logits, mask_logits = self.model(self.torch.tensor(arr[None, :, :, :], dtype=self.torch.float32))
            probs = self.torch.softmax(logits[0], dim=0).cpu().numpy()
            mask = (self.torch.sigmoid(mask_logits[0, 0]).cpu().numpy() > 0.5).astype(np.uint8)
        class_idx = int(np.argmax(probs))
        latency_ms = (time.perf_counter() - started) * 1000.0
        log.info("damage_segment_inference", latency_ms=round(latency_ms, 3), label=DAMAGE_CLASSES[class_idx])
        return DamagePrediction(
            class_label=DAMAGE_CLASSES[class_idx],
            confidence=float(probs[class_idx]),
            bounding_boxes=self._boxes_from_mask(mask),
            latency_ms=latency_ms,
        )

    @staticmethod
    def _boxes_from_mask(mask: np.ndarray) -> list[dict[str, float | str]]:
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return []
        h, w = mask.shape
        return [
            {
                "label": "damage_zone",
                "x_min": float(xs.min() / max(w, 1)),
                "y_min": float(ys.min() / max(h, 1)),
                "x_max": float(xs.max() / max(w, 1)),
                "y_max": float(ys.max() / max(h, 1)),
            }
        ]


def segment_image(image_bytes: bytes) -> dict:
    """Compatibility wrapper for older callers.

    The production damage endpoint uses checkpointed DamageSegmenter inference.
    This wrapper never fabricates model output when no checkpoint is configured.
    """
    return {
        "classes": {},
        "dominant_class": None,
        "damage_confidence": None,
        "model_version": None,
        "message": f"Received {len(image_bytes)} bytes; configure DAMAGE_MODEL_CHECKPOINT for inference.",
    }
