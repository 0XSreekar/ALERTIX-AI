import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import { registerServiceWorker } from "./lib/offline";
import { checkTokenExpiry } from "./lib/localAuth";
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
          <SessionExpiredToast />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);

registerServiceWorker();
