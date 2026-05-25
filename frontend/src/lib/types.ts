export interface HazardEvent {
  id: string;
  hazard_type: string;
  source: string;
  external_id: string | null;
  occurred_at: string;
  latitude: number | null;
  longitude: number | null;
  magnitude: number | null;
  depth_km: number | null;
  intensity: number | null;
  metadata: Record<string, unknown> | null;
  anomaly_score: number | null;
  probability: number | null;
  model_version: string | null;
  created_at: string;
}

export interface Alert {
  id: string;
  hazard_type: string;
  severity: "info" | "watch" | "warning" | "emergency";
  title: string;
  explanation: string | null;
  explanation_lang: string;
  explanation_status: "pending" | "done" | "degraded";
  probability: number | null;
  event_ids: string[];
  model_version: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface SosReport {
  id: string;
  raw_text: string;
  language: string | null;
  latitude: number | null;
  longitude: number | null;
  extracted_location_text: string | null;
  urgency_score: number | null;
  triaged: boolean;
  llm_summary: string | null;
  created_at: string;
}

export interface EarthquakePrediction {
  anomaly_score: number | null;
  aftershock_24h_probability: number | null;
  aftershock_7d_probability: number | null;
  recent_event_count: number;
  explanation: string | null;
  tsunami_risk: boolean;
  model_version: string | null;
  disclaimer: string;
}

export interface FloodForecastPoint {
  hour: number;
  discharge_p10: number;
  discharge_p50: number;
  discharge_p90: number;
}

export interface FloodPrediction {
  basin_id: string | null;
  basin_name: string | null;
  forecast: FloodForecastPoint[];
  official_bulletin_agrees: boolean | null;
  google_flood_hub_agrees?: boolean | null;
  model_version: string | null;
}

export interface WildfireCluster {
  cluster_id: number;
  centroid_lat: number;
  centroid_lon: number;
  hotspot_count: number;
  mean_frp: number;
  risk: string;
}

export interface WildfirePrediction {
  clusters: WildfireCluster[];
  total_hotspots: number;
}

export type DamageClass = "no_damage" | "minor" | "major" | "destroyed";

export interface DamageBoundingBox {
  label: string;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface DamageNearestEvent {
  id: string;
  hazard_type: string;
  title: string | null;
  distance_km: number;
  occurred_at: string | null;
}

export interface DamageResult {
  status: string;
  report_id: string;
  filename: string;
  sha256: string;
  image_url: string;
  deduplicated: boolean;
  class_label: DamageClass;
  confidence: number;
  class_probs: Record<DamageClass, number>;
  bounding_boxes: DamageBoundingBox[];
  mask_overlay: string;          // data URL
  mask_shape: [number, number];
  model_version: string;
  provider: "gemini-vision" | "cnn-synthetic" | string;
  description: string;
  visible_hazards: string[];
  latency_ms: number;
  nearest_event: DamageNearestEvent | null;
}

export interface DamageReportSummary {
  id: string;
  class_label: DamageClass;
  confidence: number;
  class_probs: Record<DamageClass, number>;
  latitude: number | null;
  longitude: number | null;
  model_version: string;
  notes: string | null;
  image_url: string;
  created_at: string | null;
}

export const DAMAGE_COLORS: Record<DamageClass, string> = {
  no_damage: "#22c55e",
  minor: "#facc15",
  major: "#f97316",
  destroyed: "#ef4444",
};

export const DAMAGE_LABELS: Record<DamageClass, string> = {
  no_damage: "No damage",
  minor: "Minor",
  major: "Major",
  destroyed: "Destroyed",
};

export interface RiskGridCell {
  lat: number;
  lon: number;
  risk_index: number;
  tier: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface RiskGridResponse {
  cells: RiskGridCell[];
  radius_km: number;
  model_version: string;
}

export interface LandslidePrediction {
  gsi_zone: string | null;
  rainfall_threshold_exceeded: boolean;
  cumulative_rainfall_mm: number | null;
  threshold_mm: number | null;
  risk_level: string;
}

export type HazardType =
  | "earthquake"
  | "flood"
  | "cyclone"
  | "wildfire"
  | "landslide"
  | "damage";

export const SEVERITY_COLORS: Record<string, string> = {
  info: "#3b82f6",
  watch: "#f59e0b",
  warning: "#f97316",
  emergency: "#ef4444",
};

export const HAZARD_COLORS: Record<HazardType, string> = {
  earthquake: "#ef4444",
  flood: "#3b82f6",
  cyclone: "#8b5cf6",
  wildfire: "#f97316",
  landslide: "#a16207",
  damage: "#6b7280",
};
