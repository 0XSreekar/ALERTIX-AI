import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import RiskGauge from "@/components/RiskGauge";
import { fetchLandslidePrediction, fetchRecentEvents } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const RISK_SCORE: Record<string, number> = {
  extreme: 1.0,
  elevated: 0.75,
  high: 0.65,
  moderate: 0.4,
  low: 0.15,
};

const RISK_LABEL: Record<string, string> = {
  extreme: "Extreme — Evacuate",
  elevated: "Elevated — High Alert",
  high: "High",
  moderate: "Moderate",
  low: "Low",
};

const GSI_LABEL: Record<string, string> = {
  very_high: "Very High (GSI Zone I)",
  high: "High (GSI Zone II)",
  moderate: "Moderate (GSI Zone III)",
  low: "Low (GSI Zone IV)",
};

// India geographic centre — used as default query point
const DEFAULT_LAT = 20.5937;
const DEFAULT_LON = 78.9629;

export default function LandslideTab() {
  const { data: eventsData, isLoading: eventsLoading } = useQuery({
    queryKey: ["events", "landslide", "recent"],
    queryFn: () => fetchRecentEvents("landslide", 48),
    refetchInterval: 300_000,
  });

  const { data: pred, isLoading: predLoading } = useQuery({
    queryKey: ["predict", "landslide", DEFAULT_LAT, DEFAULT_LON],
    queryFn: () => fetchLandslidePrediction(DEFAULT_LAT, DEFAULT_LON),
    refetchInterval: 600_000,
  });

  const riskScore = RISK_SCORE[pred?.risk_level ?? "low"] ?? 0;
  const riskLabel = RISK_LABEL[pred?.risk_level ?? "low"] ?? "Low";

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Landslide Risk</h2>
      <p className="text-sm text-muted-foreground">
        GSI landslide hazard zonation overlaid with IMD intensity-duration rainfall
        threshold rules. Rainfall data sourced live from Open-Meteo.
      </p>

      <HazardMap
        events={eventsData?.events || []}
        className="h-[400px] w-full rounded-lg lg:h-[500px]"
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rainfall Threshold Status</CardTitle>
          </CardHeader>
          <CardContent>
            {predLoading ? (
              <p className="text-sm text-muted-foreground">Fetching rainfall data…</p>
            ) : (
              <>
                <div className="mb-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">24h Rainfall</span>
                    <span className="font-medium">
                      {pred?.cumulative_rainfall_mm != null
                        ? `${pred.cumulative_rainfall_mm} mm`
                        : "Unavailable"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Trigger Threshold</span>
                    <span className="font-medium">
                      {pred?.threshold_mm != null ? `${pred.threshold_mm} mm` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Threshold Exceeded</span>
                    <span
                      className={`font-semibold ${pred?.rainfall_threshold_exceeded ? "text-red-400" : "text-green-400"}`}
                    >
                      {pred?.rainfall_threshold_exceeded ? "YES" : "No"}
                    </span>
                  </div>
                </div>
                <RiskGauge value={riskScore} label={`Risk: ${riskLabel}`} className="mt-4" />
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">GSI Hazard Zone</CardTitle>
          </CardHeader>
          <CardContent>
            {predLoading ? (
              <p className="text-sm text-muted-foreground">Loading zone data…</p>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Zone Classification</span>
                  <span className="font-semibold text-primary">
                    {pred?.gsi_zone ? (GSI_LABEL[pred.gsi_zone] ?? pred.gsi_zone) : "Unknown"}
                  </span>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Classification based on Geological Survey of India landslide hazard
                  zonation maps combined with IMD published rainfall thresholds for
                  India's landslide-prone regions.
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Showing nation-wide centre (lat {DEFAULT_LAT}, lon {DEFAULT_LON}).
                  Zoom/select a district for localised risk.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {!eventsLoading && (eventsData?.events.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Landslide Events</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2">Time</th>
                    <th className="pb-2">Source</th>
                    <th className="pb-2">Location</th>
                    <th className="pb-2">Intensity</th>
                  </tr>
                </thead>
                <tbody>
                  {eventsData!.events.slice(0, 20).map((e) => (
                    <tr key={e.id} className="border-b border-border/50">
                      <td className="py-2 text-xs">{new Date(e.occurred_at).toLocaleString()}</td>
                      <td className="py-2 text-xs">{e.source}</td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {e.latitude != null && e.longitude != null
                          ? `${e.latitude.toFixed(2)}°N, ${e.longitude.toFixed(2)}°E`
                          : "—"}
                      </td>
                      <td className="py-2">{e.intensity?.toFixed(1) ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
