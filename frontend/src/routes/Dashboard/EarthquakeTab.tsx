import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import HazardDisclaimer from "@/components/HazardDisclaimer";
import RiskGauge from "@/components/RiskGauge";
import WsStatusBadge from "@/components/WsStatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchRecentEvents, fetchEarthquakePrediction } from "@/lib/api";
import { earthquakeEventsWs } from "@/lib/ws";
import { queryKeys } from "@/lib/queryKeys";
import { Button } from "@/components/ui/button";
import type { HazardEvent } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function EarthquakeTab() {
  const [liveEvents, setLiveEvents] = useState<HazardEvent[]>([]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.events.recent("earthquake", 24),
    queryFn: () => fetchRecentEvents("earthquake", 24),
    refetchInterval: 60_000,
  });

  const { data: prediction } = useQuery({
    queryKey: queryKeys.predict.earthquake(20.5, 78.9, 500),
    queryFn: () => fetchEarthquakePrediction(20.5, 78.9, 500),
    refetchInterval: 300_000,
  });

  useEffect(() => {
    const unsub = earthquakeEventsWs.subscribe((event) => {
      setLiveEvents((prev) => [event, ...prev].slice(0, 50));
    });
    return unsub;
  }, []);

  const allEvents: HazardEvent[] = [...liveEvents, ...(data?.events ?? [])];
  const uniqueEvents: HazardEvent[] = Array.from(
    new globalThis.Map<string, HazardEvent>(allEvents.map((e) => [e.id, e])).values(),
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-2xl font-bold">Earthquake Monitor</h2>
        <div className="flex items-center gap-3">
          <WsStatusBadge ws={earthquakeEventsWs} label="Live" />
          <span className="text-sm text-muted-foreground">
            {uniqueEvents.length} events in last 24h
          </span>
        </div>
      </div>

      <HazardDisclaimer hazard="earthquake" />

      {/* Map */}
      {isLoading ? (
        <Skeleton className="h-[400px] w-full rounded-lg lg:h-[500px]" />
      ) : (
        <HazardMap events={uniqueEvents} className="h-[400px] w-full rounded-lg lg:h-[500px]" />
      )}

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <RiskGauge
          value={(prediction?.anomaly_score ?? 0) * 100}
          label="Anomaly Score"
        />
        <RiskGauge
          value={(prediction?.aftershock_24h_probability ?? 0) * 100}
          label="24h Aftershock Prob."
        />
        <RiskGauge
          value={(prediction?.aftershock_7d_probability ?? 0) * 100}
          label="7d Aftershock Prob."
        />
      </div>

      {/* Recent events table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="py-4 text-center">
              <p className="text-sm text-red-400">Failed to load events.</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => void refetch()}>
                Retry
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2">Time</th>
                    <th className="pb-2">Mag</th>
                    <th className="pb-2">Depth</th>
                    <th className="pb-2">Location</th>
                  </tr>
                </thead>
                <tbody>
                  {uniqueEvents.slice(0, 20).map((e) => (
                    <tr key={e.id} className="border-b border-border/50">
                      <td className="py-2 text-xs">
                        {new Date(e.occurred_at).toLocaleString()}
                      </td>
                      <td className="py-2 font-medium">{e.magnitude?.toFixed(1) ?? "?"}</td>
                      <td className="py-2 text-xs">{e.depth_km?.toFixed(0) ?? "?"} km</td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {(e.metadata as Record<string, unknown>)?.place as string ?? "Unknown"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
