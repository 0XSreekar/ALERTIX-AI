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

type Tab = "briefing" | "cascades" | "stats";

export default function SentinelTab() {
  const [hourOffset, setHourOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("briefing");

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
    enabled: tab === "cascades",
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

  const critical = threats.filter((t) => t.threat_score >= 0.75).length;

  return (
    <div className="space-y-4 pb-4">
      {/* ─── Clean header — title + 2 KPIs + live badge ──────────────── */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <h2 className="text-2xl font-bold">Sentinel</h2>
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
          <p className="text-xs text-muted-foreground">
            Live 3D map of every hazard happening across India right now.
            Click any dot to see the situation report.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-md border border-border/60 bg-card/40 px-3 py-1.5">
            <span className="font-mono text-base font-bold tabular-nums text-foreground">
              {allEventsOnGlobe.length}
            </span>{" "}
            <span className="text-muted-foreground">events</span>
          </span>
          {critical > 0 && (
            <span className="rounded-md border border-red-700/40 bg-red-950/30 px-3 py-1.5">
              <span className="font-mono text-base font-bold tabular-nums text-red-400">
                {critical}
              </span>{" "}
              <span className="text-red-300">critical</span>
            </span>
          )}
        </div>
      </header>

      {/* ─── Time slider — compact ──────────────────────────────────── */}
      <TimeSlider value={hourOffset} onChange={setHourOffset} />

      {/* ─── Main: Globe (left, dominant) + Threats list (right) ───── */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr),320px]">
        <div className="relative h-[600px] overflow-hidden rounded-xl border border-border/60 bg-[radial-gradient(ellipse_at_center,_rgba(15,42,68,0.5)_0%,_rgba(2,6,17,1)_75%)]">
          <Globe
            events={allEventsOnGlobe}
            selectedId={selectedId}
            onSelect={setSelectedId}
            cyclones={isLive ? forecastsData?.cyclones ?? [] : []}
            halos={isLive ? forecastsData?.halos ?? [] : []}
            autoRotate={isLive && selectedId === null}
          />

          {/* Help text — first-time users */}
          {!streamLoading && !selectedId && (
            <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 rounded-full bg-background/70 px-3 py-1 text-[11px] text-muted-foreground backdrop-blur">
              Drag to rotate · click any dot for details
            </div>
          )}

          {/* Hazard legend */}
          <div className="absolute bottom-3 left-3 rounded-lg border border-border/40 bg-background/75 p-2.5 text-[11px] backdrop-blur">
            <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
              Hazard
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(HAZARD_COLOR).map(([name, color]) => (
                <div key={name} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="capitalize text-foreground/85">{name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Threats list */}
        <div className="flex h-[600px] flex-col overflow-hidden rounded-xl border border-border/60 bg-card/40">
          <div className="border-b border-border/40 px-4 py-3">
            <h3 className="text-sm font-semibold text-foreground">
              What's happening now
            </h3>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              Top hazards in the last 6 hours
            </p>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-3">
            <ThreatList
              threats={threats}
              selectedId={selectedId}
              onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
            />
          </div>
        </div>
      </div>

      {/* ─── Single tab strip — show ONE secondary panel at a time ──── */}
      <div className="overflow-hidden rounded-xl border border-border/60 bg-card/40">
        <div className="flex border-b border-border/40">
          {(
            [
              { id: "briefing", label: "Ask AI", icon: "💬" },
              { id: "cascades", label: "Cascading hazards", icon: "🔗" },
              { id: "stats", label: "Statistics", icon: "📊" },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex flex-1 items-center justify-center gap-2 px-4 py-3 text-sm transition-colors ${
                tab === t.id
                  ? "border-b-2 border-cyan-400 bg-cyan-500/[0.08] font-medium text-cyan-200"
                  : "border-b-2 border-transparent text-muted-foreground hover:bg-secondary/30 hover:text-foreground"
              }`}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        <div className="p-4">
          {tab === "briefing" && <BriefingBar contextEventIds={contextEventIds} />}
          {tab === "cascades" && (
            <CascadeGraph
              graph={cascadeData ?? null}
              selectedId={selectedId}
              onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
            />
          )}
          {tab === "stats" && (
            <StatsPanel events={allEventsOnGlobe} cascade={cascadeData ?? null} />
          )}
        </div>
      </div>

      {/* Slide-in SitRep panel */}
      <SitRepPanel event={selectedEvent} onClose={() => setSelectedId(null)} />
    </div>
  );
}
