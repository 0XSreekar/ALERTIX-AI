import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Globe from "@/components/sentinel/Globe";
import ThreatList from "@/components/sentinel/ThreatList";
import TimeSlider from "@/components/sentinel/TimeSlider";
import BriefingBar from "@/components/sentinel/BriefingBar";
import SitRepPanel from "@/components/sentinel/SitRepPanel";
import CascadeGraph from "@/components/sentinel/CascadeGraph";
import {
  fetchSentinelCascades,
  fetchSentinelForecasts,
  fetchSentinelStream,
  fetchSentinelThreats,
} from "@/lib/api";

export default function SentinelTab() {
  const [hourOffset, setHourOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { from, to, isLive } = useMemo(() => {
    const target = new Date(Date.now() + hourOffset * 3600_000);
    const start = new Date(target.getTime() - 24 * 3600_000);
    return {
      from: start.toISOString(),
      to: target.toISOString(),
      isLive: hourOffset === 0,
    };
  }, [hourOffset]);

  const { data: streamData, isLoading: streamLoading } = useQuery({
    queryKey: ["sentinel", "stream", from, to],
    queryFn: () => fetchSentinelStream({ from, to, limit: 1500 }),
    refetchInterval: isLive ? 30_000 : false,
  });

  const { data: threatsData } = useQuery({
    queryKey: ["sentinel", "threats"],
    queryFn: () => fetchSentinelThreats(360, 12),
    refetchInterval: 45_000,
  });

  const { data: forecastsData } = useQuery({
    queryKey: ["sentinel", "forecasts"],
    queryFn: () => fetchSentinelForecasts(720),
    refetchInterval: isLive ? 90_000 : false,
    enabled: isLive,
  });

  const { data: cascadeData } = useQuery({
    queryKey: ["sentinel", "cascades"],
    queryFn: () => fetchSentinelCascades(48, 300),
    refetchInterval: 120_000,
  });

  const events = streamData?.events ?? [];
  const threats = threatsData?.threats ?? [];

  // Surface threats that aren't in the time-window stream too (they're recent
  // by definition), so the globe is never sparser than the sidebar.
  const allEventsOnGlobe = useMemo(() => {
    const seen = new Set(events.map((e) => e.id));
    const extras = threats
      .filter((t) => !seen.has(t.id))
      .map((t) => ({
        id: t.id,
        hazard_type: t.hazard_type,
        occurred_at: t.occurred_at,
        lat: t.latitude,
        lon: t.longitude,
        mag: t.magnitude,
        intensity: t.intensity,
        meta: t.metadata,
      }));
    return [...events, ...extras];
  }, [events, threats]);

  const selectedEvent = useMemo(() => {
    if (!selectedId) return null;
    return allEventsOnGlobe.find((e) => e.id === selectedId) ?? null;
  }, [selectedId, allEventsOnGlobe]);

  useEffect(() => {
    if (selectedId && !allEventsOnGlobe.find((e) => e.id === selectedId)) {
      setSelectedId(null);
    }
  }, [allEventsOnGlobe, selectedId]);

  const contextEventIds = useMemo(() => {
    const ids = new Set<string>();
    threats.forEach((t) => ids.add(t.id));
    if (selectedId) ids.add(selectedId);
    return Array.from(ids);
  }, [threats, selectedId]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="bg-gradient-to-r from-cyan-300 to-purple-300 bg-clip-text text-2xl font-bold text-transparent">
            Sentinel · Live Threat Theatre
          </h2>
          <p className="text-xs text-muted-foreground">
            3D digital twin of India · live event streams · model-driven forecast
            cones · RAG-grounded AI briefings (all citations link to real event IDs).
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
            {streamLoading ? "syncing…" : `${allEventsOnGlobe.length} events`}
          </span>
          {forecastsData && (
            <span>
              {forecastsData.cyclones.length} cyclone tracks ·{" "}
              {forecastsData.halos.length} halos
            </span>
          )}
        </div>
      </div>

      <TimeSlider value={hourOffset} onChange={setHourOffset} />

      <div className="grid gap-4 lg:grid-cols-[1fr,340px]">
        {/* Globe */}
        <div className="relative h-[620px] overflow-hidden rounded-xl border border-border bg-gradient-to-b from-slate-950 to-slate-900 shadow-2xl">
          <Globe
            events={allEventsOnGlobe}
            selectedId={selectedId}
            onSelect={setSelectedId}
            cyclones={isLive ? forecastsData?.cyclones ?? [] : []}
            halos={isLive ? forecastsData?.halos ?? [] : []}
            autoRotate={isLive && selectedId === null}
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
            {isLive && forecastsData && (
              <div className="mt-1.5 border-t border-border/40 pt-1.5 text-[10px] text-muted-foreground">
                <div>— cyclone track (purple line)</div>
                <div>○ warning halo (radius)</div>
              </div>
            )}
          </div>

          <div className="absolute right-3 top-3 rounded-md border border-cyan-700/40 bg-cyan-950/30 px-2 py-1 text-[10px] font-mono text-cyan-300 backdrop-blur">
            {isLive ? "● LIVE" : "○ replay"}
          </div>
        </div>

        {/* Side panel */}
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
              onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
            />
          </div>
        </div>
      </div>

      <CascadeGraph
        graph={cascadeData ?? null}
        selectedId={selectedId}
        onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
      />

      <BriefingBar contextEventIds={contextEventIds} />

      {/* Slide-in SitRep panel (renders only when an event is selected) */}
      <SitRepPanel event={selectedEvent} onClose={() => setSelectedId(null)} />
    </div>
  );
}
