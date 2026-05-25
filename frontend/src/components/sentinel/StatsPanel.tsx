/**
 * Stats panel — hazard distribution + 24h activity sparkline.
 * Companion to the cascade graph. Pure SVG, no chart library.
 */
import { useMemo } from "react";
import type { SentinelStreamEvent, SentinelCascadeGraph } from "@/lib/types";

const HAZARD_COLOR: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

const HAZARD_LABEL: Record<string, string> = {
  earthquake: "Earthquake",
  flood: "Flood",
  cyclone: "Cyclone",
  wildfire: "Wildfire",
  landslide: "Landslide",
};

interface Props {
  events: SentinelStreamEvent[];
  cascade: SentinelCascadeGraph | null;
}

export default function StatsPanel({ events, cascade }: Props) {
  // Hazard distribution
  const counts = useMemo(() => {
    const map = new Map<string, number>();
    events.forEach((e) => map.set(e.hazard_type, (map.get(e.hazard_type) ?? 0) + 1));
    const arr = Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
    const total = arr.reduce((s, [, n]) => s + n, 0);
    return { arr, total };
  }, [events]);

  // 24h hourly bins
  const sparkline = useMemo(() => {
    const now = Date.now();
    const BINS = 24;
    const bins = new Array<number>(BINS).fill(0);
    events.forEach((e) => {
      if (!e.occurred_at) return;
      const t = new Date(e.occurred_at).getTime();
      const ageH = (now - t) / 3600_000;
      if (ageH < 0 || ageH > 24) return;
      const idx = BINS - 1 - Math.floor(ageH);
      if (idx >= 0 && idx < BINS) bins[idx] += 1;
    });
    const max = Math.max(1, ...bins);
    return { bins, max };
  }, [events]);

  // Cascade-pair counts (edge labels)
  const cascadeTypes = useMemo(() => {
    if (!cascade) return [] as { label: string; count: number }[];
    const m = new Map<string, number>();
    cascade.edges.forEach((e) => m.set(e.label, (m.get(e.label) ?? 0) + 1));
    return Array.from(m.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({ label, count }));
  }, [cascade]);

  return (
    <div className="grid h-full content-start gap-4">
      {/* Hazard distribution */}
      <div className="rounded-xl border border-border/60 bg-card/40 p-4 backdrop-blur">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Hazard mix
          </h3>
          <span className="font-mono text-xs text-muted-foreground">
            {counts.total} events / 24h
          </span>
        </div>
        {counts.arr.length === 0 ? (
          <p className="py-2 text-xs text-muted-foreground">No events in window.</p>
        ) : (
          <div className="space-y-2.5">
            {counts.arr.map(([type, n]) => {
              const pct = (n / counts.total) * 100;
              const color = HAZARD_COLOR[type] ?? "#9ca3af";
              return (
                <div key={type}>
                  <div className="mb-1 flex items-center justify-between text-[11px]">
                    <span className="flex items-center gap-1.5 text-foreground/90">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      {HAZARD_LABEL[type] ?? type}
                    </span>
                    <span className="font-mono text-muted-foreground">
                      {n} · {pct.toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-secondary/40">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.85 }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 24h sparkline */}
      <div className="rounded-xl border border-border/60 bg-card/40 p-4 backdrop-blur">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Activity · 24h
          </h3>
          <span className="font-mono text-xs text-muted-foreground">
            peak {sparkline.max}
          </span>
        </div>
        <svg
          viewBox="0 0 240 80"
          preserveAspectRatio="none"
          className="h-20 w-full"
          aria-label="Hourly event activity"
        >
          <defs>
            <linearGradient id="spark-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
          </defs>
          {(() => {
            const W = 240;
            const H = 80;
            const step = W / (sparkline.bins.length - 1);
            const pts = sparkline.bins.map((v, i) => {
              const x = i * step;
              const y = H - (v / sparkline.max) * (H - 8) - 4;
              return [x, y] as const;
            });
            const linePath = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ");
            const fillPath = `${linePath} L${W},${H} L0,${H} Z`;
            return (
              <>
                <path d={fillPath} fill="url(#spark-fill)" />
                <path d={linePath} stroke="#22d3ee" strokeWidth={1.5} fill="none" />
                {pts.map(([x, y], i) => (
                  <circle key={i} cx={x} cy={y} r={1.4} fill="#67e8f9" />
                ))}
              </>
            );
          })()}
        </svg>
        <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
          <span>-24h</span>
          <span>-12h</span>
          <span>now</span>
        </div>
      </div>

      {/* Cascade patterns */}
      <div className="rounded-xl border border-border/60 bg-card/40 p-4 backdrop-blur">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Cascade patterns
          </h3>
          {cascade && (
            <span className="font-mono text-xs text-muted-foreground">
              {cascade.edges.length} links
            </span>
          )}
        </div>
        {cascadeTypes.length === 0 ? (
          <p className="py-2 text-xs text-muted-foreground">
            No cascading hazards detected.
          </p>
        ) : (
          <div className="space-y-1.5">
            {cascadeTypes.slice(0, 5).map(({ label, count }) => (
              <div
                key={label}
                className="flex items-center justify-between rounded-md bg-secondary/30 px-2.5 py-1.5 text-xs"
              >
                <span className="truncate text-foreground/85">{label}</span>
                <span className="ml-2 rounded-full bg-cyan-900/40 px-2 py-0.5 font-mono text-[10px] text-cyan-300">
                  ×{count}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
