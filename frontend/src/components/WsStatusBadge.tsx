import { useEffect, useState } from "react";
import type { WsStatus } from "@/lib/ws";

interface WsStatusBadgeProps {
  ws: { subscribeStatus: (handler: (s: WsStatus) => void) => () => void };
  label?: string;
}

const STATUS_CONFIG: Record<WsStatus, { text: string; dot: string }> = {
  connected: { text: "Connected", dot: "bg-green-400" },
  connecting: { text: "Connecting…", dot: "bg-yellow-400 animate-pulse" },
  reconnecting: { text: "Reconnecting…", dot: "bg-orange-400 animate-pulse" },
  disconnected: { text: "Disconnected", dot: "bg-red-500" },
};

export default function WsStatusBadge({ ws, label }: WsStatusBadgeProps) {
  const [status, setStatus] = useState<WsStatus>("disconnected");

  useEffect(() => {
    const unsub = ws.subscribeStatus(setStatus);
    return unsub;
  }, [ws]);

  const cfg = STATUS_CONFIG[status];

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/60 px-2.5 py-1 text-xs text-muted-foreground backdrop-blur-sm">
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {label ? `${label}: ` : ""}{cfg.text}
    </span>
  );
}
