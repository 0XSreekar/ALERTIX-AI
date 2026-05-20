import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import RiskGauge from "@/components/RiskGauge";
import { fetchRecentEvents, fetchEarthquakePrediction } from "@/lib/api";
import { earthquakeEventsWs } from "@/lib/ws";
import type { HazardEvent } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function EarthquakeTab() {
  const [liveEvents, setLiveEvents] = useState<HazardEvent[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ["events", "earthquake", "recent"],
    queryFn: () => fetchRecentEvents("earthquake", 24),
    refetchInterval: 60_000,
  });

  const { data: prediction } = useQuery({
    queryKey: ["predict", "earthquake"],
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
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Earthquake Monitor</h2>
        <span className="text-sm text-muted-foreground">
          {uniqueEvents.length} events in last 24h
        </span>
      </div>

      {/* Disclaimer */}
      <div className="rounded-lg border border-yellow-600/30 bg-yellow-600/5 p-3 text-xs text-yellow-300">
        Alertix AI does not perform deterministic earthquake prediction. Values shown represent
        statistical anomaly scores and aftershock probabilities derived from recent seismicity.
        Always follow official warnings from NCS and IMD.
      </div>

      {/* Map */}
      <HazardMap
        events={uniqueEvents}
        className="h-[400px] w-full rounded-lg lg:h-[500px]"
      />

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-3">
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
            <p className="text-sm text-muted-foreground">Loading...</p>
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
