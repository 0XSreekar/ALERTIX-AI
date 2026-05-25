import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Globe from "@/components/sentinel/Globe";
import ThreatList from "@/components/sentinel/ThreatList";
import TimeSlider from "@/components/sentinel/TimeSlider";
import BriefingBar from "@/components/sentinel/BriefingBar";
import SitRepPanel from "@/components/sentinel/SitRepPanel";
import CascadeGraph from "@/components/sentinel/CascadeGraph";
import StatsPanel from "@/components/sentinel/StatsPanel";
import {
  fetchSentinelCascades,
  fetchSentinelForecasts,
  fetchSentinelStream,
  fetchSentinelThreats,
} from "@/lib/api";

const HAZARD_COLOR: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

function StatChip({ value, label, hint }: { value: string | number; label: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-card/40 px-3 py-2 backdrop-blur">
      <div className="font-mono text-lg font-bold leading-none tabular-nums text-foreground">
        {value}
      </div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
        {label}
      </div>
      {hint && <div className="text-[10px] text-muted-foreground/70">{hint}</div>}
    </div>
  );
}

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

  // Header stats
  const critical = threats.filter((t) => t.threat_score >= 0.75).length;
  const high = threats.filter((t) => t.threat_score >= 0.55 && t.threat_score < 0.75).length;
  const cycloneCount = forecastsData?.cyclones.length ?? 0;
  const cascadeEdges = cascadeData?.edges.length ?? 0;

  return (
    <div className="space-y-4 pb-4">
      {/* ─── Header bar ─────────────────────────────────────────────── */}
      <header className="relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-r from-slate-950/80 via-slate-900/70 to-slate-950/80 backdrop-blur">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent" />
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 lg:p-5">
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded-full bg-cyan-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">
                Sentinel
              </span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-mono font-bold ${
                  isLive
                    ? "bg-green-500/15 text-green-300"
                    : "bg-amber-500/15 text-amber-300"
                }`}
              >
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    isLive ? "animate-pulse bg-green-400" : "bg-amber-400"
                  }`}
                />
                {isLive ? "LIVE" : "REPLAY"}
              </span>
            </div>
            <h2 className="bg-gradient-to-r from-cyan-200 via-purple-200 to-cyan-200 bg-clip-text text-2xl font-bold tracking-tight text-transparent">
              Live Threat Theatre
            </h2>
            <p className="mt-1 max-w-xl text-xs text-muted-foreground">
              3D digital twin of India · live event streams · model-driven
              forecast cones · RAG-grounded AI briefings citing real event IDs.
            </p>
          </div>
          <div className="grid flex-shrink-0 grid-cols-4 gap-2">
            <StatChip value={allEventsOnGlobe.length} label="On globe" hint="24h window" />
            <StatChip value={critical} label="Critical" hint={`${high} high`} />
            <StatChip value={cycloneCount} label="Tracks" hint="cyclone forecasts" />
            <StatChip value={cascadeEdges} label="Cascades" hint="linked hazards" />
          </div>
        </div>
      </header>

      {/* ─── Time slider ───────────────────────────────────────────── */}
      <TimeSlider value={hourOffset} onChange={setHourOffset} />

      {/* ─── Globe + Threats sidebar ───────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr),360px]">
        {/* Globe panel */}
        <div className="relative h-[640px] overflow-hidden rounded-xl border border-border/60 bg-[radial-gradient(ellipse_at_center,_rgba(15,42,68,0.6)_0%,_rgba(2,6,17,1)_70%)] shadow-[inset_0_0_60px_rgba(0,0,0,0.6)]">
          {/* Subtle grid texture */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(34,211,238,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.5) 1px, transparent 1px)",
              backgroundSize: "32px 32px",
            }}
          />
          <Globe
            events={allEventsOnGlobe}
            selectedId={selectedId}
            onSelect={setSelectedId}
            cyclones={isLive ? forecastsData?.cyclones ?? [] : []}
            halos={isLive ? forecastsData?.halos ?? [] : []}
            autoRotate={isLive && selectedId === null}
          />

          {/* Corner brackets — gives it the ops-room feel */}
          <CornerBrackets />

          {/* Hazard legend */}
          <div className="absolute bottom-4 left-4 rounded-lg border border-border/40 bg-background/70 p-2.5 text-[11px] shadow-xl backdrop-blur-md">
            <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Hazard
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(HAZARD_COLOR).map(([name, color]) => (
                <div key={name} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full shadow-[0_0_6px_currentColor]"
                    style={{ backgroundColor: color, color }}
                  />
                  <span className="capitalize text-foreground/85">{name}</span>
                </div>
              ))}
            </div>
            {isLive && (
              <div className="mt-2 space-y-0.5 border-t border-border/40 pt-1.5 text-[10px] text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <span className="inline-block h-0.5 w-3 bg-purple-400" />
                  cyclone forecast track
                </div>
                <div className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full border border-sky-300"
                    style={{ backgroundColor: "transparent" }}
                  />
                  warning radius halo
                </div>
              </div>
            )}
          </div>

          {/* Camera hint */}
          <div className="absolute right-4 top-4 rounded-md border border-cyan-700/30 bg-cyan-950/40 px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.15em] text-cyan-300 shadow-lg backdrop-blur">
            {streamLoading
              ? "syncing…"
              : selectedId
                ? "tracking event"
                : isLive
                  ? "auto-orbit"
                  : "replay"}
          </div>
        </div>

        {/* Threats sidebar */}
        <div className="flex h-[640px] flex-col gap-3">
          <div className="flex-1 overflow-hidden rounded-xl border border-border/60 bg-card/40 backdrop-blur">
            <div className="border-b border-border/40 px-4 py-3">
              <div className="flex items-baseline justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Top live threats
                </h3>
                <span className="font-mono text-[10px] text-muted-foreground">
                  last 6h
                </span>
              </div>
            </div>
            <div className="h-full overflow-y-auto px-3 py-3">
              <ThreatList
                threats={threats}
                selectedId={selectedId}
                onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ─── Cascade graph + Stats panel ───────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr),360px]">
        <CascadeGraph
          graph={cascadeData ?? null}
          selectedId={selectedId}
          onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
        />
        <StatsPanel events={allEventsOnGlobe} cascade={cascadeData ?? null} />
      </div>

      {/* ─── AI Briefing Bar ───────────────────────────────────────── */}
      <BriefingBar contextEventIds={contextEventIds} />

      {/* Slide-in SitRep panel */}
      <SitRepPanel event={selectedEvent} onClose={() => setSelectedId(null)} />
    </div>
  );
}

function CornerBrackets() {
  // Subtle technical-readout corner ticks on the globe panel
  const cls =
    "pointer-events-none absolute h-5 w-5 border-cyan-400/40";
  return (
    <>
      <div className={`${cls} left-2 top-2 border-l-2 border-t-2`} />
      <div className={`${cls} right-2 top-2 border-r-2 border-t-2`} />
      <div className={`${cls} bottom-2 left-2 border-b-2 border-l-2`} />
      <div className={`${cls} bottom-2 right-2 border-b-2 border-r-2`} />
    </>
  );
}
