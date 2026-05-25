import type { SentinelThreat } from "@/lib/types";

const COLORS: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

function tier(score: number): { label: string; color: string } {
  if (score >= 0.75) return { label: "CRITICAL", color: "#ef4444" };
  if (score >= 0.55) return { label: "HIGH", color: "#f97316" };
  if (score >= 0.35) return { label: "MEDIUM", color: "#facc15" };
  return { label: "LOW", color: "#22c55e" };
}

interface Props {
  threats: SentinelThreat[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ThreatList({ threats, selectedId, onSelect }: Props) {
  if (threats.length === 0) {
    return (
      <p className="px-2 py-4 text-xs text-muted-foreground">
        No live hazards in the current window.
      </p>
    );
  }
  return (
    <div className="space-y-1.5">
      {threats.map((t) => {
        const t2 = tier(t.threat_score);
        const isSelected = selectedId === t.id;
        return (
          <button
            key={t.id}
            onClick={() => onSelect(t.id)}
            className={`flex w-full items-start gap-2 rounded-md border p-2 text-left text-xs transition-colors ${
              isSelected
                ? "border-primary/60 bg-primary/10"
                : "border-border hover:border-border/80 hover:bg-accent/40"
            }`}
          >
            <span
              className="mt-1 inline-block h-2 w-2 flex-shrink-0 rounded-full"
              style={{ backgroundColor: COLORS[t.hazard_type] ?? "#9ca3af" }}
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium text-foreground">
                  {t.title}
                </span>
                <span
                  className="rounded px-1.5 py-0.5 text-[10px] font-bold"
                  style={{ backgroundColor: t2.color + "22", color: t2.color }}
                >
                  {t2.label}
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                {t.hazard_type} · {t.occurred_at ? new Date(t.occurred_at).toLocaleTimeString() : "—"}
                {" · "}
                <span className="font-mono">
                  {t.latitude.toFixed(1)}, {t.longitude.toFixed(1)}
                </span>
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
