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
