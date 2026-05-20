import type {
  Alert,
  EarthquakePrediction,
  FloodPrediction,
  HazardEvent,
  LandslidePrediction,
  SosReport,
  WildfirePrediction,
} from "./types";
import { getToken } from "./localAuth";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = { ...authHeaders(), ...init?.headers };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ── Events ──────────────────────────────────────────────────
export function fetchEvents(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch<{ events: HazardEvent[]; total: number }>(`/api/events${qs}`);
}

export function fetchRecentEvents(hazardType?: string, hours = 24) {
  const qs = new URLSearchParams({ hours: String(hours) });
  if (hazardType) qs.set("hazard_type", hazardType);
  return apiFetch<{ events: HazardEvent[] }>(`/api/events/recent?${qs}`);
}

export function fetchEvent(id: string) {
  return apiFetch<HazardEvent>(`/api/events/${id}`);
}

// ── Alerts ──────────────────────────────────────────────────
export function fetchAlerts(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch<{ alerts: Alert[] }>(`/api/alerts${qs}`);
}

export function fetchAlert(id: string) {
  return apiFetch<Alert>(`/api/alerts/${id}`);
}

// ── SOS ─────────────────────────────────────────────────────
export function submitSos(body: {
  raw_text: string;
  language?: string;
  latitude?: number;
  longitude?: number;
  consent_given: boolean;
}) {
  return apiFetch<{ id: string }>("/api/sos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchMySos() {
  return apiFetch<{ reports: SosReport[] }>("/api/sos/mine");
}

export function fetchSosFeed(minUrgency = 3) {
  return apiFetch<{ reports: SosReport[] }>(`/api/sos/feed?min_urgency=${minUrgency}`);
}

// ── Predictions ─────────────────────────────────────────────
export function fetchEarthquakePrediction(lat: number, lon: number, radiusKm = 200) {
  return apiFetch<EarthquakePrediction>(
    `/api/predict/earthquake?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`,
  );
}

export function fetchFloodPrediction(basinId: string) {
  return apiFetch<FloodPrediction>(`/api/predict/flood?basin_id=${basinId}`);
}

export function fetchWildfirePrediction(bbox = "65,5,100,40") {
  return apiFetch<WildfirePrediction>(`/api/predict/wildfire?bbox=${bbox}`);
}

export function fetchLandslidePrediction(lat: number, lon: number) {
  return apiFetch<LandslidePrediction>(`/api/predict/landslide?lat=${lat}&lon=${lon}`);
}

// ── Contact ─────────────────────────────────────────────────
export function submitContact(body: { name: string; email: string; message: string }) {
  return apiFetch<{ status: string }>("/api/contact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── Damage ──────────────────────────────────────────────────
export function uploadDamageImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<{ status: string; classes: Record<string, number> }>("/api/damage/segment", {
    method: "POST",
    body: form,
  });
}
