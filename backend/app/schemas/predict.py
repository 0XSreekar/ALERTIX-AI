from pydantic import BaseModel


class EarthquakePrediction(BaseModel):
    anomaly_score: float | None = None
    aftershock_24h_probability: float | None = None
    aftershock_7d_probability: float | None = None
    recent_event_count: int = 0
    explanation: str | None = None
    tsunami_risk: bool = False
    model_version: str | None = None
    disclaimer: str = (
        "Alertix AI does not perform deterministic earthquake prediction. "
        "Values shown represent statistical anomaly scores and aftershock "
        "probabilities derived from recent seismicity. Always follow official "
        "warnings from NCS and IMD."
    )


class FloodForecastPoint(BaseModel):
    hour: int
    discharge_p10: float
    discharge_p50: float
    discharge_p90: float


class FloodPrediction(BaseModel):
    basin_id: str | None = None
    basin_name: str | None = None
    forecast: list[FloodForecastPoint] = []
    official_bulletin_agrees: bool | None = None
    model_version: str | None = None


class CyclonePrediction(BaseModel):
    storm_id: str | None = None
    storm_name: str | None = None
    current_lat: float | None = None
    current_lon: float | None = None
    category: str | None = None
    wind_speed_kmh: float | None = None
    track_points: list[dict] = []
    impact_radius_km: float | None = None


class WildfireCluster(BaseModel):
    centroid_lat: float
    centroid_lon: float
    size: int
    avg_frp: float | None = None
    risk_level: str
    earliest: str | None = None
    latest: str | None = None


class WildfirePrediction(BaseModel):
    clusters: list[WildfireCluster] = []
    total_hotspots: int = 0


class LandslidePrediction(BaseModel):
    gsi_zone: str | None = None
    rainfall_threshold_exceeded: bool = False
    cumulative_rainfall_mm: float | None = None
    threshold_mm: float | None = None
    risk_level: str = "low"
