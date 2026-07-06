import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import HazardDisclaimer from "@/components/HazardDisclaimer";
import { fetchRecentEvents } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

export default function WildfireTab() {
  const { data } = useQuery({
    queryKey: ["events", "wildfire", "recent"],
    queryFn: () => fetchRecentEvents("wildfire", 24),
    refetchInterval: 300_000,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Wildfire Hotspots</h2>
      <HazardDisclaimer hazard="wildfire" />
      <p className="text-sm text-muted-foreground">
        NASA FIRMS VIIRS/MODIS active fire detections in the last 24 hours.
        Phase 2 will add DBSCAN clustering and risk classification.
      </p>

      <HazardMap
        events={data?.events || []}
        className="h-[400px] w-full rounded-lg lg:h-[500px]"
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold">{data?.events.length ?? 0}</p>
            <p className="text-xs text-muted-foreground">Active Hotspots</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold">—</p>
            <p className="text-xs text-muted-foreground">Clusters (Phase 2)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold">
              {data?.events.length
                ? (
                    data.events.reduce((s, e) => s + (e.intensity || 0), 0) / data.events.length
                  ).toFixed(1)
                : "—"}
            </p>
            <p className="text-xs text-muted-foreground">Avg FRP (MW)</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
