import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import RiskGauge from "@/components/RiskGauge";
import { fetchRecentEvents } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const BASINS = ["krishna", "godavari", "mahanadi", "yamuna", "brahmaputra"];

export default function FloodTab() {
  const { data: eventsData, isLoading } = useQuery({
    queryKey: ["events", "flood", "recent"],
    queryFn: () => fetchRecentEvents("flood", 48),
    refetchInterval: 120_000,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Flood Monitor</h2>

      <HazardMap
        events={eventsData?.events || []}
        className="h-[400px] w-full rounded-lg lg:h-[500px]"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {BASINS.map((basin) => (
          <Card key={basin}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm capitalize">{basin} Basin</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                72-hour discharge forecast will be available in Phase 2 (LSTM model).
              </p>
              <RiskGauge value={0} label="Flood Risk" className="mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Flood Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : eventsData?.events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No flood events in the last 48 hours.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2">Time</th>
                    <th className="pb-2">Source</th>
                    <th className="pb-2">Level/Intensity</th>
                    <th className="pb-2">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {eventsData?.events.slice(0, 20).map((e) => (
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
