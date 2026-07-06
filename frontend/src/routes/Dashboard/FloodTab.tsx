import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import HazardDisclaimer from "@/components/HazardDisclaimer";
import RiskGauge from "@/components/RiskGauge";
import { fetchFloodPrediction, fetchRecentEvents } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FloodPrediction } from "@/lib/types";

const BASINS = [
  { id: "krishna", label: "Krishna" },
  { id: "godavari", label: "Godavari" },
  { id: "mahanadi", label: "Mahanadi" },
  { id: "yamuna", label: "Yamuna" },
  { id: "brahmaputra", label: "Brahmaputra" },
];

function gfhIntensityToRisk(pred: FloodPrediction | undefined): number {
  if (!pred || pred.forecast.length === 0) return 0;
  const latest = pred.forecast[pred.forecast.length - 1];
  // GFH intensity: danger=3, warning=2, watch=1, normal=0 — normalise to 0-1
  return Math.min(1, latest.discharge_p50 / 3);
}

function gfhStatusLabel(pred: FloodPrediction | undefined): string {
  if (!pred || pred.forecast.length === 0) return "No data";
  const latest = pred.forecast[pred.forecast.length - 1];
  if (latest.discharge_p50 >= 3) return "DANGER";
  if (latest.discharge_p50 >= 2) return "Warning";
  if (latest.discharge_p50 >= 1) return "Watch";
  return "Normal";
}

function BasinCard({ basin }: { basin: (typeof BASINS)[0] }) {
  const { data: pred, isLoading } = useQuery({
    queryKey: ["flood", "predict", basin.id],
    queryFn: () => fetchFloodPrediction(basin.id),
    refetchInterval: 300_000,
  });

  const risk = gfhIntensityToRisk(pred);
  const status = gfhStatusLabel(pred);
  const gfhAgrees = pred?.google_flood_hub_agrees;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-sm">
          <span>{basin.label} Basin</span>
          {!isLoading && (
            <span
              className={`text-xs font-semibold ${
                status === "DANGER"
                  ? "text-red-400"
                  : status === "Warning"
                    ? "text-orange-400"
                    : status === "Watch"
                      ? "text-yellow-400"
                      : "text-green-400"
              }`}
            >
              {status}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-xs text-muted-foreground">Loading…</p>
        ) : (
          <>
            <RiskGauge value={risk} label="Flood Risk" className="mb-2" />
            {gfhAgrees != null && (
              <p className="text-xs text-muted-foreground">
                Google Flood Hub:{" "}
                <span className={gfhAgrees ? "text-orange-400" : "text-green-400"}>
                  {gfhAgrees ? "Elevated risk confirmed" : "Normal"}
                </span>
              </p>
            )}
            {pred && pred.forecast.length > 0 && (
              <p className="mt-1 text-xs text-muted-foreground">
                {pred.forecast.length} gauge readings · {pred.model_version}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function FloodTab() {
  const { data: eventsData, isLoading } = useQuery({
    queryKey: ["events", "flood", "recent"],
    queryFn: () => fetchRecentEvents("flood", 48),
    refetchInterval: 120_000,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Flood Monitor</h2>
      <HazardDisclaimer hazard="flood" />
      <p className="text-sm text-muted-foreground">
        Live data from Google Flood Hub (GFH) and CWC India river gauges.
        Risk levels: Normal → Watch → Warning → DANGER.
      </p>

      <HazardMap
        events={eventsData?.events || []}
        className="h-[400px] w-full rounded-lg lg:h-[500px]"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {BASINS.map((basin) => (
          <BasinCard key={basin.id} basin={basin} />
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Flood Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (eventsData?.events.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No flood events in the last 48 hours.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2">Time</th>
                    <th className="pb-2">Source</th>
                    <th className="pb-2">Level / Intensity</th>
                    <th className="pb-2">Basin / Gauge</th>
                  </tr>
                </thead>
                <tbody>
                  {eventsData!.events.slice(0, 20).map((e) => (
                    <tr key={e.id} className="border-b border-border/50">
                      <td className="py-2 text-xs">{new Date(e.occurred_at).toLocaleString()}</td>
                      <td className="py-2 text-xs">{e.source}</td>
                      <td className="py-2">{e.intensity?.toFixed(1) ?? "?"}</td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {(e.metadata as Record<string, unknown>)?.basin as string ??
                          (e.metadata as Record<string, unknown>)?.gauge_name as string ??
                          "—"}
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
