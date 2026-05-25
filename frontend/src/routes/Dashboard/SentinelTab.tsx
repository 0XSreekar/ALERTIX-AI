import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Globe from "@/components/sentinel/Globe";
import ThreatList from "@/components/sentinel/ThreatList";
import TimeSlider from "@/components/sentinel/TimeSlider";
import BriefingBar from "@/components/sentinel/BriefingBar";
import { fetchSentinelStream, fetchSentinelThreats } from "@/lib/api";

export default function SentinelTab() {
  const [hourOffset, setHourOffset] = useState(0); // 0 = now
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Time window: events from (target - 24h) to target
  const { from, to } = useMemo(() => {
    const target = new Date(Date.now() + hourOffset * 3600_000);
    const start = new Date(target.getTime() - 24 * 3600_000);
    return { from: start.toISOString(), to: target.toISOString() };
  }, [hourOffset]);

  const { data: streamData, isLoading: streamLoading } = useQuery({
    queryKey: ["sentinel", "stream", from, to],
    queryFn: () => fetchSentinelStream({ from, to, limit: 1500 }),
    refetchInterval: hourOffset === 0 ? 30_000 : false,
  });

  const { data: threatsData } = useQuery({
    queryKey: ["sentinel", "threats"],
    queryFn: () => fetchSentinelThreats(360, 12),
    refetchInterval: 45_000,
  });

  const events = streamData?.events ?? [];
  const threats = threatsData?.threats ?? [];

  // Pulse selection from threat list to globe and vice versa
  const handleSelectThreat = (id: string) => {
    setSelectedId(id === selectedId ? null : id);
  };

  // Build context event IDs from visible threats + selected
  const contextEventIds = useMemo(() => {
    const ids = new Set<string>();
    threats.forEach((t) => ids.add(t.id));
    if (selectedId) ids.add(selectedId);
    return Array.from(ids);
  }, [threats, selectedId]);

  const selectedEvent = useMemo(() => {
    if (!selectedId) return null;
    return events.find((e) => e.id === selectedId) ?? null;
  }, [selectedId, events]);

  useEffect(() => {
    // Reset selection when scrubbing to a window the selected event isn't in
    if (selectedId && !events.find((e) => e.id === selectedId)) {
      setSelectedId(null);
    }
  }, [events, selectedId]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="bg-gradient-to-r from-cyan-300 to-purple-300 bg-clip-text text-2xl font-bold text-transparent">
            Sentinel · Live Threat Theatre
          </h2>
          <p className="text-xs text-muted-foreground">
            Real-time multi-hazard digital twin of India. Every dot is a real
            event. AI briefings cite event IDs — never invents data.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
            {streamLoading ? "syncing…" : `${events.length} events on globe`}
          </span>
        </div>
      </div>

      {/* Time slider */}
      <TimeSlider value={hourOffset} onChange={setHourOffset} />

      {/* Main grid: globe (large) + side panel */}
      <div className="grid gap-4 lg:grid-cols-[1fr,340px]">
        {/* Globe — keep aspect ratio with a fixed-height wrapper */}
        <div className="relative h-[600px] overflow-hidden rounded-xl border border-border bg-gradient-to-b from-slate-950 to-slate-900 shadow-2xl">
          <Globe
            events={events}
            selectedId={selectedId}
            onSelect={setSelectedId}
            autoRotate={hourOffset === 0 && selectedId === null}
          />
          {/* Hazard legend */}
          <div className="absolute bottom-3 left-3 rounded-md border border-border/50 bg-background/70 p-2 text-[11px] backdrop-blur">
            <div className="mb-1 font-semibold uppercase tracking-wider text-muted-foreground">
              Hazard
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
              {[
                ["earthquake", "#ef4444"],
                ["flood", "#38bdf8"],
                ["cyclone", "#a78bfa"],
                ["wildfire", "#f97316"],
                ["landslide", "#92400e"],
              ].map(([name, color]) => (
                <div key={name} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="capitalize">{name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Selected event mini-card */}
          {selectedEvent && (
            <div className="absolute right-3 top-3 max-w-xs rounded-md border border-primary/40 bg-background/85 p-3 text-xs shadow-lg backdrop-blur">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-semibold uppercase text-foreground">
                  {selectedEvent.hazard_type}
                </span>
                <button
                  onClick={() => setSelectedId(null)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  ✕
                </button>
              </div>
              <p className="text-muted-foreground">
                {(selectedEvent.meta as { title?: string; place?: string })?.title ??
                  (selectedEvent.meta as { place?: string })?.place ??
                  "—"}
              </p>
              <div className="mt-2 grid grid-cols-2 gap-y-1 text-[11px]">
                <span className="text-muted-foreground">When</span>
                <span className="font-mono">
                  {selectedEvent.occurred_at
                    ? new Date(selectedEvent.occurred_at).toLocaleString()
                    : "—"}
                </span>
                <span className="text-muted-foreground">Loc</span>
                <span className="font-mono">
                  {selectedEvent.lat.toFixed(2)}, {selectedEvent.lon.toFixed(2)}
                </span>
                {selectedEvent.mag != null && (
                  <>
                    <span className="text-muted-foreground">Mag</span>
                    <span className="font-mono">{selectedEvent.mag.toFixed(1)}</span>
                  </>
                )}
                {selectedEvent.intensity != null && (
                  <>
                    <span className="text-muted-foreground">Intensity</span>
                    <span className="font-mono">{selectedEvent.intensity.toFixed(2)}</span>
                  </>
                )}
              </div>
              <p className="mt-2 border-t border-border pt-2 text-[10px] text-muted-foreground">
                Drill-down SitRep panel · coming Day 2
              </p>
            </div>
          )}
        </div>

        {/* Side panel: top threats */}
        <div className="space-y-3">
          <div className="rounded-lg border border-border bg-card/60 p-3">
            <div className="mb-2 flex items-center justify-between text-xs">
              <h3 className="font-semibold uppercase tracking-wider text-muted-foreground">
                Top Live Threats
              </h3>
              <span className="text-muted-foreground">last 6h</span>
            </div>
            <ThreatList
              threats={threats}
              selectedId={selectedId}
              onSelect={handleSelectThreat}
            />
          </div>
        </div>
      </div>

      {/* AI Briefing Bar */}
      <BriefingBar contextEventIds={contextEventIds} />
    </div>
  );
}
