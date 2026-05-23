import type {
  Alert,
  EarthquakePrediction,
  FloodPrediction,
  HazardEvent,
  LandslidePrediction,
  SosReport,
  WildfirePrediction,
} from "./types";
import { getToken, clearSession, checkTokenExpiry } from "./localAuth";
import { cacheAlerts, queueCitizenReport } from "./offline";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Fires a toast-like notification using the global toast queue (if available). */
function notifySessionExpired() {
  // Dispatch a custom event; the ToastProvider in main.tsx listens for it.
  window.dispatchEvent(new CustomEvent("alertix:session-expired"));
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  // Check token expiry before every API call
  checkTokenExpiry();

  const headers = { ...authHeaders(), ...init?.headers };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    clearSession();
    notifySessionExpired();
    // Redirect to /login — works inside and outside React Router context
    window.location.href = "/login";
    throw new Error("Session expired");
  }

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
  return apiFetch<{ alerts: Alert[] }>(`/api/alerts${qs}`).then((data) => {
    cacheAlerts(data.alerts);
    return data;
  });
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

export async function submitCitizenReport(body: {
  hazard_type: string;
  description: string;
  latitude: number;
  longitude: number;
  media_url?: string | null;
}) {
  if (!navigator.onLine) {
    queueCitizenReport(body);
    return { status: "queued-offline" };
  }
  return apiFetch<{ id: string; status: string }>("/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── Admin ────────────────────────────────────────────────────

export interface AdminUser {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AdminAlert {
  id: string;
  hazard_type: string;
  severity: string;
  title: string;
  explanation: string | null;
  created_at: string;
  expires_at: string | null;
  status: string;
  latitude: number | null;
  longitude: number | null;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  user_id: string | null;
  details: Record<string, unknown> | null;
}

export interface SystemStatus {
  backend_version: string;
  redis_status: string;
  db_status: string;
  env_config: Record<string, string>;
}

export function fetchAdminUsers(page = 0, pageSize = 50) {
  return apiFetch<{ users: AdminUser[]; total: number }>(
    `/api/admin/users?skip=${page * pageSize}&limit=${pageSize}`,
  );
}

export function updateUserRole(userId: string, role: string) {
  return apiFetch<{ status: string }>(`/api/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
}

export function deactivateUser(userId: string) {
  return apiFetch<{ status: string }>(`/api/admin/users/${userId}/deactivate`, {
    method: "POST",
  });
}

export function fetchAdminAlerts(page = 0, pageSize = 50) {
  return apiFetch<{ alerts: AdminAlert[]; total: number }>(
    `/api/admin/alerts?skip=${page * pageSize}&limit=${pageSize}`,
  );
}

export function acknowledgeAlert(alertId: string) {
  return apiFetch<{ status: string }>(`/api/admin/alerts/${alertId}/acknowledge`, {
    method: "POST",
  });
}

export function dismissAlert(alertId: string) {
  return apiFetch<{ status: string }>(`/api/admin/alerts/${alertId}/dismiss`, {
    method: "POST",
  });
}

export function fetchAuditLog(page = 0, pageSize = 50) {
  return apiFetch<{ entries: AuditLogEntry[]; total: number }>(
    `/api/admin/audit-log?skip=${page * pageSize}&limit=${pageSize}`,
  );
}

export function fetchSystemStatus() {
  return apiFetch<SystemStatus>("/api/admin/system-status");
}
