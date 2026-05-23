import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import AlertCard from "@/components/AlertCard";
import { Skeleton } from "@/components/ui/skeleton";
import WsStatusBadge from "@/components/WsStatusBadge";
import { fetchAlerts } from "@/lib/api";
import { alertsWs } from "@/lib/ws";
import { queryKeys } from "@/lib/queryKeys";
import { Button } from "@/components/ui/button";
import type { Alert } from "@/lib/types";

export default function AlertsTab() {
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.alerts.all,
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
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-2xl font-bold">Active Alerts</h2>
        <div className="flex items-center gap-3">
          <WsStatusBadge ws={alertsWs} label="Live" />
          <span className="text-sm text-muted-foreground">
            {uniqueAlerts.length} active alert{uniqueAlerts.length !== 1 && "s"}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-red-800/40 bg-red-950/20 p-8 text-center">
          <p className="text-sm text-red-400">Failed to load alerts.</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => void refetch()}>
            Retry
          </Button>
        </div>
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
