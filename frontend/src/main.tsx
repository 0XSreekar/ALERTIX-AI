import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import { alertsWs } from "./lib/ws";
import { registerServiceWorker } from "./lib/offline";
import { checkTokenExpiry } from "./lib/localAuth";
import type { Alert } from "./lib/types";
import "./styles/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// Check token expiry on startup
checkTokenExpiry();

/** Toast shown when a new alert arrives via WebSocket. */
function AlertToast() {
  const [alert, setAlert] = useState<Alert | null>(null);

  useEffect(() => {
    const unsub = alertsWs.subscribe((incoming) => {
      setAlert(incoming);
      const timeout = setTimeout(() => setAlert(null), 8000);
      return () => clearTimeout(timeout);
    });
    return unsub;
  }, []);

  if (!alert) return null;

  const sev = alert.severity as string;
  const isCritical = sev === "critical" || sev === "high" || sev === "emergency";

  return (
    <div
      className={`fixed bottom-6 right-6 z-[9999] max-w-sm rounded-lg border px-4 py-3 shadow-lg ${
        isCritical
          ? "border-red-500/50 bg-red-950 text-red-100"
          : "border-orange-500/30 bg-orange-950/80 text-orange-100"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider opacity-70">
            {isCritical ? "🚨 Alert" : "⚠️ Alert"} · {alert.hazard_type}
          </p>
          <p className="mt-1 text-sm font-medium">{alert.title}</p>
        </div>
        <button
          onClick={() => setAlert(null)}
          className="shrink-0 text-xs opacity-60 hover:opacity-100"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

/** Simple toast shown when the 401 interceptor fires. */
function SessionExpiredToast() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handler = () => {
      setVisible(true);
      setTimeout(() => setVisible(false), 5000);
    };
    window.addEventListener("alertix:session-expired", handler);
    return () => window.removeEventListener("alertix:session-expired", handler);
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex items-center gap-3 rounded-lg border border-border bg-background px-4 py-3 shadow-lg">
      <span className="text-sm text-foreground">Session expired — please log in again</span>
      <button
        onClick={() => setVisible(false)}
        className="ml-2 text-xs text-muted-foreground hover:text-foreground"
      >
        ✕
      </button>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
          <AlertToast />
          <SessionExpiredToast />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);

registerServiceWorker();
