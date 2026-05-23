"""LSTM flood forecasting model with checkpointed weights."""

from __future__ import annotations

import json
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
        raise RuntimeError("Install alertix-backend[ml] to use FloodLSTM") from exc
    return torch, nn


@dataclass(frozen=True, slots=True)
class FloodForecast:
    forecast_24h: float
    forecast_48h: float
    forecast_72h: float
    risk_tier: str
    latency_ms: float


class FloodLSTM:
    def __init__(
        self, input_size: int = 2, hidden_size: int = 48, checkpoint: str | Path | None = None
    ) -> None:
        torch, nn = _torch()

        class _Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size, hidden_size=hidden_size, batch_first=True
                )
                self.head = nn.Sequential(nn.Linear(hidden_size, 32), nn.ReLU(), nn.Linear(32, 3))

            def forward(self, x):  # type: ignore[no-untyped-def]
                output, _ = self.lstm(x)
                return self.head(output[:, -1, :])

        self.torch = torch
        self.model = _Model()
        self.metrics: dict[str, float] = {}
        self.loaded = False
        if checkpoint:
            self.load(checkpoint)

    @staticmethod
    def _risk(max_level: float) -> str:
        if max_level >= 1.0:
            return "CRITICAL"
        if max_level >= 0.75:
            return "HIGH"
        if max_level >= 0.45:
            return "MEDIUM"
        return "LOW"

    def train_model(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray,
        y_val: np.ndarray,
        *,
        epochs: int = 25,
        lr: float = 1e-3,
    ) -> dict[str, float]:
        torch = self.torch
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        loss_fn = torch.nn.MSELoss()
        train_x = torch.tensor(x_train, dtype=torch.float32)
        train_y = torch.tensor(y_train, dtype=torch.float32)
        val_x = torch.tensor(x_val, dtype=torch.float32)
        val_y = torch.tensor(y_val, dtype=torch.float32)
        for _ in range(max(1, epochs)):
            optimizer.zero_grad()
            loss = loss_fn(self.model(train_x), train_y)
            loss.backward()
            optimizer.step()
        self.model.eval()
        with torch.no_grad():
            pred = self.model(val_x)
            err = pred - val_y
            rmse = float(torch.sqrt(torch.mean(err**2)).item())
            mae = float(torch.mean(torch.abs(err)).item())
        self.metrics = {"rmse": rmse, "mae": mae}
        self.loaded = True
        return self.metrics

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.torch.save({"state_dict": self.model.state_dict(), "metrics": self.metrics}, path)
        path.with_suffix(path.suffix + ".json").write_text(
            json.dumps(self.metrics), encoding="utf-8"
        )

    def load(self, path: str | Path) -> None:
        path = Path(path)
        from app.config import get_settings

        settings = get_settings()
        if not path.exists():
            if settings.require_model_weights:
                raise RuntimeError(f"FloodLSTM checkpoint not found: {path}")
            log.info("flood_lstm_checkpoint_missing, continuing without weights: %s", path)
            return
        checkpoint = self.torch.load(path, map_location="cpu")
        self.model.load_state_dict(checkpoint["state_dict"])
        self.metrics = dict(checkpoint.get("metrics") or {})
        self.model.eval()
        self.loaded = True

    def predict(self, seven_day_history: np.ndarray) -> FloodForecast:
        if not self.loaded:
            raise RuntimeError("FloodLSTM checkpoint is not loaded")
        history = np.asarray(seven_day_history, dtype=np.float32)
        if history.shape != (7, 2):
            raise ValueError("seven_day_history must have shape (7, 2): rainfall_mm, river_level_m")
        started = time.perf_counter()
        with self.torch.no_grad():
            pred = self.model(self.torch.tensor(history[None, :, :], dtype=self.torch.float32))[
                0
            ].numpy()
        latency_ms = (time.perf_counter() - started) * 1000.0
        max_forecast = float(np.max(pred))
        log.info("flood_lstm_inference", latency_ms=round(latency_ms, 3))
        return FloodForecast(
            forecast_24h=float(pred[0]),
            forecast_48h=float(pred[1]),
            forecast_72h=float(pred[2]),
            risk_tier=self._risk(max_forecast),
            latency_ms=latency_ms,
        )
