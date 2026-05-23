"""U-Net flood extent segmentation with checkpointed weights."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)


def _torch() -> Any:
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("Install alertix-backend[ml] to use FloodUNet") from exc
    return torch, nn


@dataclass(frozen=True, slots=True)
class FloodMaskPrediction:
    mask: np.ndarray
    affected_area_km2: float
    latency_ms: float


class FloodUNet:
    def __init__(self, in_channels: int = 4, checkpoint: str | Path | None = None) -> None:
        torch, nn = _torch()

        def block(cin: int, cout: int):
            return nn.Sequential(
                nn.Conv2d(cin, cout, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(cout, cout, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
            )

        class _UNet(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.enc1 = block(in_channels, 32)
                self.pool1 = nn.MaxPool2d(2)
                self.enc2 = block(32, 64)
                self.pool2 = nn.MaxPool2d(2)
                self.mid = block(64, 128)
                self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
                self.dec2 = block(128, 64)
                self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
                self.dec1 = block(64, 32)
                self.out = nn.Conv2d(32, 1, kernel_size=1)

            def forward(self, x):  # type: ignore[no-untyped-def]
                e1 = self.enc1(x)
                e2 = self.enc2(self.pool1(e1))
                mid = self.mid(self.pool2(e2))
                d2 = self.up2(mid)
                d2 = self.dec2(torch.cat([d2, e2], dim=1))
                d1 = self.up1(d2)
                d1 = self.dec1(torch.cat([d1, e1], dim=1))
                return self.out(d1)

        self.torch = torch
        self.model = _UNet()
        self.loaded = False
        self.metrics: dict[str, float] = {}
        if checkpoint:
            self.load(checkpoint)

    @staticmethod
    def metrics_from_masks(pred: np.ndarray, target: np.ndarray) -> dict[str, float]:
        pred_bool = pred.astype(bool)
        target_bool = target.astype(bool)
        tp = float(np.logical_and(pred_bool, target_bool).sum())
        fp = float(np.logical_and(pred_bool, ~target_bool).sum())
        fn = float(np.logical_and(~pred_bool, target_bool).sum())
        iou = tp / max(tp + fp + fn, 1.0)
        f1 = (2 * tp) / max(2 * tp + fp + fn, 1.0)
        return {"iou": iou, "f1": f1}

    def train_model(self, x: np.ndarray, y: np.ndarray, *, epochs: int = 10, lr: float = 1e-3) -> dict[str, float]:
        torch = self.torch
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        loss_fn = torch.nn.BCEWithLogitsLoss()
        tx = torch.tensor(x, dtype=torch.float32)
        ty = torch.tensor(y, dtype=torch.float32)
        if ty.ndim == 3:
            ty = ty[:, None, :, :]
        for _ in range(max(1, epochs)):
            optimizer.zero_grad()
            loss = loss_fn(self.model(tx), ty)
            loss.backward()
            optimizer.step()
        self.model.eval()
        with torch.no_grad():
            mask = (torch.sigmoid(self.model(tx)) > 0.5).cpu().numpy()
        self.metrics = self.metrics_from_masks(mask, ty.cpu().numpy())
        self.loaded = True
        return self.metrics

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.torch.save({"state_dict": self.model.state_dict(), "metrics": self.metrics}, path)

    def load(self, path: str | Path) -> None:
        path = Path(path)
        from app.config import get_settings

        settings = get_settings()
        if not path.exists():
            if settings.require_model_weights:
                raise RuntimeError(f"FloodUNet checkpoint not found: {path}")
            log.info("flood_unet_checkpoint_missing, continuing without weights: %s", path)
            return
        checkpoint = self.torch.load(path, map_location="cpu")
        self.model.load_state_dict(checkpoint["state_dict"])
        self.metrics = dict(checkpoint.get("metrics") or {})
        self.model.eval()
        self.loaded = True

    def predict(self, image: np.ndarray, pixel_area_m2: float = 100.0) -> FloodMaskPrediction:
        if not self.loaded:
            raise RuntimeError("FloodUNet checkpoint is not loaded")
        arr = np.asarray(image, dtype=np.float32)
        if arr.ndim != 3:
            raise ValueError("image must have shape (channels, height, width)")
        started = time.perf_counter()
        with self.torch.no_grad():
            logits = self.model(self.torch.tensor(arr[None, :, :, :], dtype=self.torch.float32))
            mask = (self.torch.sigmoid(logits)[0, 0].cpu().numpy() > 0.5).astype(np.uint8)
        area = float(mask.sum() * pixel_area_m2 / 1_000_000.0)
        latency_ms = (time.perf_counter() - started) * 1000.0
        log.info("flood_unet_inference", latency_ms=round(latency_ms, 3), area_km2=area)
        return FloodMaskPrediction(mask=mask, affected_area_km2=area, latency_ms=latency_ms)
