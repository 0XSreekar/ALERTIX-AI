import { useEffect, useState } from "react";

const HOURS_BACK = 24 * 7;
const HOURS_FORWARD = 72;
const TOTAL = HOURS_BACK + HOURS_FORWARD;

interface Props {
  value: number;
  onChange: (hourOffset: number) => void;
  liveTickSeconds?: number;
}

export default function TimeSlider({ value, onChange, liveTickSeconds = 60 }: Props) {
  const [isLive, setIsLive] = useState(value === 0);

  useEffect(() => {
    if (!isLive) return;
    onChange(0);
    const id = setInterval(() => onChange(0), liveTickSeconds * 1000);
    return () => clearInterval(id);
  }, [isLive, onChange, liveTickSeconds]);

  const sliderValue = value + HOURS_BACK;
  const now = new Date();
  const target = new Date(now.getTime() + value * 3600_000);
  const label =
    value === 0 ? "now" : value < 0 ? `${-value}h ago` : `+${value}h ahead`;
  const tickColor = value === 0 ? "#22c55e" : value < 0 ? "#a78bfa" : "#f97316";

  // Percent position of the "now" marker (zero hour offset)
  const nowPct = (HOURS_BACK / TOTAL) * 100;

  return (
    <div className="overflow-hidden rounded-xl border border-border/60 bg-card/40 backdrop-blur">
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLive((s) => !s)}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.15em] transition-all ${
              isLive
                ? "bg-green-500/20 text-green-300 shadow-[0_0_12px_rgba(34,197,94,0.3)]"
                : "bg-secondary text-muted-foreground hover:bg-secondary/80"
            }`}
          >
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                isLive ? "animate-pulse bg-green-400" : "bg-muted-foreground"
              }`}
            />
            Live
          </button>
          <div className="text-[11px]">
            <span className="font-mono text-muted-foreground">
              {target.toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            viewing
          </span>
          <span className="rounded-md px-2 py-0.5 font-mono text-xs font-bold" style={{ color: tickColor, backgroundColor: tickColor + "1a" }}>
            {label}
          </span>
        </div>
      </div>
      <div className="relative px-4 pb-3">
        <input
          type="range"
          min={0}
          max={TOTAL}
          step={1}
          value={sliderValue}
          onChange={(e) => {
            setIsLive(false);
            onChange(Number(e.target.value) - HOURS_BACK);
          }}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-gradient-to-r from-purple-500/30 via-cyan-400/30 to-amber-500/30 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-background [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(34,211,238,0.6)]"
        />
        {/* Now marker line */}
        <div
          className="pointer-events-none absolute top-3 h-3 w-0.5 bg-green-400/70 shadow-[0_0_4px_rgba(74,222,128,0.6)]"
          style={{ left: `calc(1rem + ${nowPct}% - 1px)` }}
        />
        <div className="mt-1.5 flex justify-between text-[9px] font-medium uppercase tracking-wider text-muted-foreground/70">
          <span>-7d</span>
          <span>-3d</span>
          <span className="text-green-400/80">now</span>
          <span>+24h</span>
          <span>+72h</span>
        </div>
      </div>
    </div>
  );
}
