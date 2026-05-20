import type { Alert } from "./types";

const ALERTS_KEY = "alertix:last-alerts";
const REPORT_QUEUE_KEY = "alertix:queued-reports";

export interface QueuedCitizenReport {
  hazard_type: string;
  description: string;
  latitude: number;
  longitude: number;
  media_url?: string | null;
  queued_at: string;
}

export function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    });
  }
}

export function cacheAlerts(alerts: Alert[]) {
  localStorage.setItem(ALERTS_KEY, JSON.stringify(alerts.slice(0, 50)));
}

export function getCachedAlerts(): Alert[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(ALERTS_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function queueCitizenReport(report: Omit<QueuedCitizenReport, "queued_at">) {
  const current = getQueuedCitizenReports();
  current.push({ ...report, queued_at: new Date().toISOString() });
  localStorage.setItem(REPORT_QUEUE_KEY, JSON.stringify(current));
}

export function getQueuedCitizenReports(): QueuedCitizenReport[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(REPORT_QUEUE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function syncQueuedCitizenReports(apiBase: string, token?: string | null) {
  if (!navigator.onLine) return;
  const queued = getQueuedCitizenReports();
  const remaining: QueuedCitizenReport[] = [];
  for (const report of queued) {
    try {
      const response = await fetch(`${apiBase}/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(report),
      });
      if (!response.ok) remaining.push(report);
    } catch {
      remaining.push(report);
    }
  }
  localStorage.setItem(REPORT_QUEUE_KEY, JSON.stringify(remaining));
}
