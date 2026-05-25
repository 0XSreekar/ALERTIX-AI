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


class RiskIndexFeatures(BaseModel):
    eq_count_30d: float = 0
    eq_max_magnitude: float = 0
    flood_max_intensity: float = 0
    rainfall_72h_mm: float = 0
    wildfire_count_24h: float = 0
    cyclone_wind_kmh: float = 0
    landslide_rule_score: float = 0


class RiskIndexPrediction(BaseModel):
    lat: float
    lon: float
    radius_km: float
    risk_index: float | None = None
    tier: str = "LOW"
    features: RiskIndexFeatures
    model_version: str = "phase2-xgboost-fusion"


class RiskGridCell(BaseModel):
    lat: float
    lon: float
    risk_index: float
    tier: str


class RiskGridResponse(BaseModel):
    cells: list[RiskGridCell]
    radius_km: float
    model_version: str = "phase2-xgboost-fusion"
