"""Omori-Utsu aftershock model.

This module deliberately estimates only statistical aftershock likelihood after
an observed mainshock. It does not predict exact earthquake time, location, or
magnitude.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from statistics import NormalDist

from app.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class OmoriParameters:
    k: float
    c: float
    p: float


@dataclass(frozen=True, slots=True)
class AftershockPrediction:
    probability: float
    risk_level: str
    confidence_interval: tuple[float, float]
    expected_count: float
    parameters: OmoriParameters
    latency_ms: float


class OmoriUtsuModel:
    def __init__(self, parameters: OmoriParameters | None = None) -> None:
        self.parameters = parameters or OmoriParameters(k=0.35, c=0.08, p=1.08)

    @staticmethod
    def _integral(params: OmoriParameters, start_days: float, end_days: float) -> float:
        start = max(0.0, start_days)
        end = max(start, end_days)
        if math.isclose(params.p, 1.0):
            return params.k * math.log((end + params.c) / (start + params.c))
        exponent = 1.0 - params.p
        return params.k * (((end + params.c) ** exponent) - ((start + params.c) ** exponent)) / exponent

    @staticmethod
    def _risk(probability: float) -> str:
        if probability >= 0.75:
            return "critical"
        if probability >= 0.5:
            return "high"
        if probability >= 0.25:
            return "medium"
        return "low"

    def fit(self, aftershock_elapsed_days: list[float]) -> OmoriParameters:
        """Fit c and p by grid-search likelihood, then derive k from count."""
        samples = sorted(t for t in aftershock_elapsed_days if t >= 0.0)
        if not samples:
            self.parameters = OmoriParameters(k=0.01, c=0.08, p=1.08)
            return self.parameters

        horizon = max(samples[-1], 1.0)
        best: tuple[float, OmoriParameters] | None = None
        for c_i in range(1, 101):
            c = c_i / 100.0
            for p_i in range(80, 181):
                p = p_i / 100.0
                base = OmoriParameters(k=1.0, c=c, p=p)
                exposure = self._integral(base, 0.0, horizon)
                if exposure <= 0:
                    continue
                k = len(samples) / exposure
                params = OmoriParameters(k=k, c=c, p=p)
                log_likelihood = sum(math.log(max(1e-12, k / ((t + c) ** p))) for t in samples)
                log_likelihood -= self._integral(params, 0.0, horizon)
                if best is None or log_likelihood > best[0]:
                    best = (log_likelihood, params)
        self.parameters = best[1] if best else self.parameters
        return self.parameters

    def predict(
        self,
        mainshock_magnitude: float,
        elapsed_hours: float,
        region: str = "india",
        horizon_hours: float = 24.0,
    ) -> AftershockPrediction:
        started = time.perf_counter()
        if mainshock_magnitude < 0.0 or mainshock_magnitude > 10.0:
            raise ValueError("mainshock magnitude must be between 0 and 10")
        if elapsed_hours < 0.0:
            raise ValueError("elapsed hours must be non-negative")

        magnitude_factor = max(0.2, 10 ** (0.45 * (mainshock_magnitude - 5.0)))
        params = OmoriParameters(
            k=self.parameters.k * magnitude_factor,
            c=self.parameters.c,
            p=self.parameters.p,
        )
        start_days = elapsed_hours / 24.0
        end_days = (elapsed_hours + horizon_hours) / 24.0
        expected = max(0.0, self._integral(params, start_days, end_days))
        probability = 1.0 - math.exp(-expected)
        z = NormalDist().inv_cdf(0.975)
        se = math.sqrt(max(expected, 1e-9))
        lower_count = max(0.0, expected - z * se)
        upper_count = expected + z * se
        ci = (1.0 - math.exp(-lower_count), 1.0 - math.exp(-upper_count))
        latency_ms = (time.perf_counter() - started) * 1000.0
        log.info(
            "omori_prediction",
            region=region,
            magnitude=mainshock_magnitude,
            probability=probability,
            latency_ms=round(latency_ms, 3),
        )
        return AftershockPrediction(
            probability=round(probability, 4),
            risk_level=self._risk(probability),
            confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
            expected_count=round(expected, 4),
            parameters=params,
            latency_ms=latency_ms,
        )


def omori_aftershock_probability(mainshock_magnitude: float, elapsed_hours: float) -> float:
    return OmoriUtsuModel().predict(mainshock_magnitude, elapsed_hours).probability
