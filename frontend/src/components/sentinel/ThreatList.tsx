import type { SentinelThreat } from "@/lib/types";

const COLORS: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

function tier(score: number): { label: string; color: string; bg: string } {
  if (score >= 0.75) return { label: "CRITICAL", color: "#ef4444", bg: "rgba(239,68,68,0.15)" };
  if (score >= 0.55) return { label: "HIGH", color: "#f97316", bg: "rgba(249,115,22,0.15)" };
  if (score >= 0.35) return { label: "MED", color: "#facc15", bg: "rgba(250,204,21,0.15)" };
  return { label: "LOW", color: "#22c55e", bg: "rgba(34,197,94,0.15)" };
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

interface Props {
  threats: SentinelThreat[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ThreatList({ threats, selectedId, onSelect }: Props) {
  if (threats.length === 0) {
    return (
      <p className="px-2 py-6 text-center text-xs text-muted-foreground">
        No live hazards in the current window.
      </p>
    );
  }
  return (
    <ul className="space-y-1.5">
      {threats.map((t) => {
        const t2 = tier(t.threat_score);
        const color = COLORS[t.hazard_type] ?? "#9ca3af";
        const isSelected = selectedId === t.id;
        return (
          <li key={t.id}>
            <button
              onClick={() => onSelect(t.id)}
              className={`group relative flex w-full items-start gap-2.5 overflow-hidden rounded-lg border p-2.5 text-left transition-all ${
                isSelected
                  ? "border-cyan-500/50 bg-cyan-500/[0.08] shadow-[inset_0_0_0_1px_rgba(34,211,238,0.15)]"
                  : "border-border/60 bg-background/30 hover:border-border hover:bg-accent/30"
              }`}
            >
              {/* Left ribbon */}
              <span
                className="absolute left-0 top-0 h-full w-0.5 transition-opacity"
                style={{ backgroundColor: color, opacity: isSelected ? 1 : 0.5 }}
              />
              {/* Hazard dot */}
              <span
                className="mt-0.5 inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full shadow-[0_0_8px_currentColor]"
                style={{ backgroundColor: color, color }}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-medium text-foreground">
                    {t.title}
                  </span>
                  <span
                    className="flex-shrink-0 rounded-md px-1.5 py-0.5 text-[9px] font-bold tabular-nums tracking-wider"
                    style={{ backgroundColor: t2.bg, color: t2.color }}
                  >
                    {t2.label}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span className="capitalize">{t.hazard_type}</span>
                  <span className="opacity-50">·</span>
                  <span className="font-mono">{timeAgo(t.occurred_at)} ago</span>
                  <span className="opacity-50">·</span>
                  <span className="font-mono tabular-nums">
                    {t.latitude.toFixed(1)}, {t.longitude.toFixed(1)}
                  </span>
                  {t.source === "demo_seed" && (
                    <span className="ml-auto rounded bg-yellow-500/20 px-1.5 py-0 font-mono text-[9px] font-bold text-yellow-300">
                      DEMO
                    </span>
                  )}
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
