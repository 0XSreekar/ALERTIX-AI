import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import AlertCard from "@/components/AlertCard";
import { fetchAlerts } from "@/lib/api";
import { alertsWs } from "@/lib/ws";
import type { Alert } from "@/lib/types";

export default function AlertsTab() {
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => fetchAlerts(),
    refetchInterval: 60_000,
  });

  useEffect(() => {
    const unsub = alertsWs.subscribe((alert) => {
      setLiveAlerts((prev) => [alert, ...prev].slice(0, 50));
    });
    return unsub;
  }, []);

  const allAlerts = [...liveAlerts, ...(data?.alerts || [])];
  const uniqueAlerts = Array.from(new Map(allAlerts.map((a) => [a.id, a])).values());

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Active Alerts</h2>
        <span className="text-sm text-muted-foreground">
          {uniqueAlerts.length} active alert{uniqueAlerts.length !== 1 && "s"}
        </span>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading alerts...</p>
      ) : uniqueAlerts.length === 0 ? (
        <div className="rounded-lg border p-8 text-center">
          <p className="text-lg font-medium">No active alerts</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Alerts are generated automatically when hazard events cross severity thresholds.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {uniqueAlerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
