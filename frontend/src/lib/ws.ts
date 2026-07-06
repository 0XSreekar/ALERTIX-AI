import type { Alert, HazardEvent } from "./types";
import { getWsTicket } from "./localAuth";

type MessageHandler<T> = (data: T) => void;
type StatusHandler = (status: WsStatus) => void;

export type WsStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || `ws://${window.location.host}`;

const MIN_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;

class AlertixWebSocket<T> {
  private ws: WebSocket | null = null;
  private path: string;
  private handlers: Set<MessageHandler<T>> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectDelay = MIN_RECONNECT_MS;
  private destroyed = false;
  private _status: WsStatus = "disconnected";

  constructor(path: string) {
    this.path = path;
  }

  /** Build the full WS URL with a fresh 60s auth ticket appended. */
  private async buildAuthedUrl(): Promise<string | null> {
    const ticket = await getWsTicket();
    if (!ticket) return null;
    const sep = this.path.includes("?") ? "&" : "?";
    return `${WS_BASE}${this.path}${sep}token=${encodeURIComponent(ticket)}`;
  }

  get status(): WsStatus {
    return this._status;
  }

  private setStatus(s: WsStatus) {
    this._status = s;
    this.statusHandlers.forEach((h) => h(s));
  }

  async connect() {
    if (this.destroyed) return;
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.setStatus("connecting");
    const url = await this.buildAuthedUrl();
    if (!url) {
      // No session — surface as disconnected; ProtectedRoute will redirect to /login.
      this.setStatus("disconnected");
      return;
    }
    if (this.destroyed) return;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectDelay = MIN_RECONNECT_MS; // reset backoff on success
      this.setStatus("connected");
      this.pingTimer = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send("ping");
        }
      }, 30_000);
    };

    this.ws.onmessage = (event) => {
      if (event.data === "pong") return;
      try {
        const data = JSON.parse(event.data as string) as T;
        this.handlers.forEach((h) => h(data));
      } catch {
        // ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      this.cleanupTimers();
      if (this.destroyed) {
        this.setStatus("disconnected");
        return;
      }
      this.setStatus("reconnecting");
      const delay = this.reconnectDelay;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_MS);
      this.reconnectTimer = setTimeout(() => {
        if (!this.destroyed) void this.connect();
      }, delay);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  subscribe(handler: MessageHandler<T>) {
    this.handlers.add(handler);
    if (this.handlers.size === 1) void this.connect();
    return () => {
      this.handlers.delete(handler);
      if (this.handlers.size === 0) this.disconnect();
    };
  }

  subscribeStatus(handler: StatusHandler) {
    this.statusHandlers.add(handler);
    handler(this._status); // immediately emit current status
    return () => this.statusHandlers.delete(handler);
  }

  disconnect() {
    this.destroyed = true;
    this.cleanupTimers();
    this.ws?.close();
    this.ws = null;
    this.setStatus("disconnected");
  }

  /** Reconnect from scratch (e.g., after page regains network). */
  reconnect() {
    this.destroyed = false;
    this.reconnectDelay = MIN_RECONNECT_MS;
    this.cleanupTimers();
    this.ws?.close();
    void this.connect();
  }

  private cleanupTimers() {
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
