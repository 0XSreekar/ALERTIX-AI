import { useEffect, useState } from "react";
import { fetchSentinelImpact, postSentinelSitRep } from "@/lib/api";
import type { SentinelImpact, SentinelSitRep, SentinelStreamEvent } from "@/lib/types";

interface Props {
  event: SentinelStreamEvent | null;
  onClose: () => void;
}

const HAZARD_COLOR: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

function MarkdownLight({ md }: { md: string }) {
  // Tiny markdown renderer — headings (##) + bold (**) + lists (- )
  const lines = md.split(/\r?\n/);
  return (
    <div className="space-y-2 text-sm leading-relaxed text-foreground/90">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) {
          return (
            <h4 key={i} className="mt-3 text-sm font-semibold uppercase tracking-wide text-cyan-300">
              {line.slice(3)}
            </h4>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <h3 key={i} className="text-base font-bold text-foreground">
              {line.slice(2)}
            </h3>
          );
        }
        if (/^[-*]\s/.test(line)) {
          return (
            <div key={i} className="flex gap-2 pl-2">
              <span className="text-cyan-400">•</span>
              <span dangerouslySetInnerHTML={{ __html: inline(line.replace(/^[-*]\s/, "")) }} />
            </div>
          );
        }
        if (line.trim() === "") return <div key={i} className="h-1" />;
        return (
          <p key={i} dangerouslySetInnerHTML={{ __html: inline(line) }} />
        );
      })}
    </div>
  );
}

function inline(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, '<code class="rounded bg-secondary px-1 py-0.5 text-xs">$1</code>')
    .replace(
      /\[(evt-[a-f0-9]+)\]/g,
      '<span class="font-mono text-cyan-300 bg-cyan-900/30 rounded px-1">[$1]</span>',
    );
}

export default function SitRepPanel({ event, onClose }: Props) {
  const [impact, setImpact] = useState<SentinelImpact | null>(null);
  const [sitrep, setSitRep] = useState<SentinelSitRep | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setImpact(null);
    setSitRep(null);
    setError("");
    if (!event) return;
    let cancelled = false;
    setLoading(true);
    // Fetch impact + SitRep in parallel
    Promise.all([
      fetchSentinelImpact(event.id).catch((e) => {
        throw new Error(`impact: ${e}`);
      }),
      postSentinelSitRep(event.id, "official").catch((e) => {
        throw new Error(`sitrep: ${e}`);
      }),
    ])
      .then(([imp, sr]) => {
        if (cancelled) return;
        setImpact(imp);
        setSitRep(sr);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [event]);

  if (!event) return null;

  const color = HAZARD_COLOR[event.hazard_type] ?? "#9ca3af";
  const title =
    (event.meta as { title?: string; place?: string }).title ??
    (event.meta as { place?: string }).place ??
    event.hazard_type;
  const popLakh = impact ? (impact.population_at_risk_thousand / 100).toFixed(1) : null;
  const isDemo = event.source === "demo_seed";

  return (
    <aside
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto border-l border-border bg-card/95 shadow-2xl backdrop-blur-md"
      role="complementary"
    >
      {/* Header */}
      <div
        className="sticky top-0 z-10 border-b border-border bg-card/95 p-4 backdrop-blur"
        style={{ borderTop: `4px solid ${color}` }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color }}>
              {event.hazard_type}
            </p>
            <h3 className="truncate text-base font-bold">{title}</h3>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "—"}
              {" · "}
              <span className="font-mono">
                {event.lat.toFixed(3)}, {event.lon.toFixed(3)}
              </span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="space-y-5 p-4">
        {isDemo && (
          <div className="rounded-lg border-2 border-yellow-500/60 bg-yellow-950/30 p-3">
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-yellow-300">
              <span className="text-base leading-none">⚠</span>
              Demo event — not a real ongoing situation
            </p>
            <p className="mt-1 text-[11px] text-yellow-200/80">
              This event came from <code className="rounded bg-yellow-900/40 px-1">backend/scripts/seed_demo_events.py</code>,
              not from live ingestion (USGS, IMD, CWC, FIRMS…). All numbers, citizens,
              and recommended actions below are illustrative only. To see real data,
              wait for live USGS earthquake events, or configure NASA FIRMS / IMD keys
              and re-run ingestion.
            </p>
          </div>
        )}

        {/* Impact block */}
        <div className="rounded-lg border border-border bg-background/50 p-3">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Population at Risk
          </p>
          {impact ? (
            <>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold tabular-nums text-cyan-300">
                  {popLakh ?? "—"}
                </span>
                <span className="pb-1 text-sm text-muted-foreground">lakh</span>
              </div>
              <p className="text-xs text-muted-foreground">
                in {impact.city_count} city/town{impact.city_count !== 1 ? "s" : ""} within{" "}
                {impact.radius_km.toFixed(0)} km
              </p>
              {impact.cities.length > 0 && (
                <ul className="mt-3 space-y-1 border-t border-border pt-3">
                  {impact.cities.slice(0, 8).map((c) => (
                    <li
                      key={`${c.name}-${c.state}`}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="truncate">
                        <span className="font-medium">{c.name}</span>
                        <span className="text-muted-foreground">, {c.state}</span>
                      </span>
                      <span className="ml-2 flex flex-shrink-0 items-center gap-2 text-muted-foreground">
                        <span className="font-mono">{c.distance_km}km</span>
                        <span className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[10px]">
                          {(c.population_thousand / 100).toFixed(1)}L
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-[10px] text-muted-foreground/70 italic">
                {impact.estimate_note}
              </p>
            </>
          ) : loading ? (
            <p className="text-xs text-muted-foreground">Calculating exposure…</p>
          ) : (
            <p className="text-xs text-muted-foreground">No impact data available.</p>
          )}
        </div>

        {/* SitRep markdown */}
        <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-cyan-300">
              AI Situation Report
            </p>
            {sitrep && (
              <span className="rounded bg-cyan-800/30 px-1.5 py-0.5 font-mono text-[10px] text-cyan-200">
                {sitrep.provider}
              </span>
            )}
          </div>
          {sitrep ? (
            <MarkdownLight md={sitrep.sitrep_markdown} />
          ) : loading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="h-2 animate-pulse rounded bg-secondary/60"
                  style={{ width: `${80 - i * 12}%` }}
                />
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">SitRep unavailable.</p>
          )}
        </div>

        {error && (
          <div className="rounded-md border border-red-800/40 bg-red-950/20 p-2 text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Raw metadata */}
        {Object.keys(event.meta).length > 0 && (
          <details className="rounded-lg border border-border bg-background/30 p-3">
            <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Raw event metadata
            </summary>
            <pre className="mt-2 overflow-x-auto rounded bg-background p-2 text-[10px]">
              {JSON.stringify(event.meta, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </aside>
  );
}
