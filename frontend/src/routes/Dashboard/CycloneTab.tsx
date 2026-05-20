import { useQuery } from "@tanstack/react-query";
import HazardMap from "@/components/Map";
import { fetchRecentEvents } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CycloneTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["events", "cyclone", "recent"],
    queryFn: () => fetchRecentEvents("cyclone", 168),
    refetchInterval: 300_000,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Cyclone Tracker</h2>

      <HazardMap
        events={data?.events || []}
        className="h-[400px] w-full rounded-lg lg:h-[500px]"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active Cyclone Bulletins</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading IMD bulletins...</p>
          ) : data?.events.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active cyclone bulletins in the last 7 days.
            </p>
          ) : (
            <div className="space-y-3">
              {data?.events.map((e) => {
                const meta = e.metadata as Record<string, unknown> | null;
                return (
                  <div key={e.id} className="rounded-lg border p-3">
                    <p className="font-medium">{meta?.title as string ?? "Cyclone Event"}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(e.occurred_at).toLocaleString()}
                    </p>
                    {typeof meta?.summary === "string" && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {meta.summary.slice(0, 300)}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
