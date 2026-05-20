import type { Alert, HazardEvent } from "./types";

type MessageHandler<T> = (data: T) => void;

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || `ws://${window.location.host}`;

class AlertixWebSocket<T> {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Set<MessageHandler<T>> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;

  constructor(path: string) {
    this.url = `${WS_BASE}${path}`;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.pingTimer = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send("ping");
        }
      }, 30_000);
    };

    this.ws.onmessage = (event) => {
      if (event.data === "pong") return;
      try {
        const data = JSON.parse(event.data) as T;
        this.handlers.forEach((h) => h(data));
      } catch {
        // ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      this.cleanup();
      this.reconnectTimer = setTimeout(() => this.connect(), 5000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  subscribe(handler: MessageHandler<T>) {
    this.handlers.add(handler);
    if (this.handlers.size === 1) this.connect();
    return () => {
      this.handlers.delete(handler);
      if (this.handlers.size === 0) this.disconnect();
    };
  }

  disconnect() {
    this.cleanup();
    this.ws?.close();
    this.ws = null;
  }

  private cleanup() {
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.pingTimer = null;
    this.reconnectTimer = null;
  }
}

export const alertsWs = new AlertixWebSocket<Alert>("/ws/alerts");
export const earthquakeEventsWs = new AlertixWebSocket<HazardEvent>(
  "/ws/events?hazard_type=earthquake",
);
export const floodEventsWs = new AlertixWebSocket<HazardEvent>("/ws/events?hazard_type=flood");
