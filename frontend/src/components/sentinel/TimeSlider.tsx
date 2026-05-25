import { useEffect, useState } from "react";

const HOURS_BACK = 24 * 7;
const HOURS_FORWARD = 72;
const TOTAL = HOURS_BACK + HOURS_FORWARD; // 240

interface Props {
  /** Hour offset from now: negative = past, positive = future, 0 = live */
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

  const sliderValue = value + HOURS_BACK; // 0..TOTAL
  const now = new Date();
  const target = new Date(now.getTime() + value * 3600_000);
  const label =
    value === 0
      ? "Now"
      : value < 0
        ? `${-value}h ago`
        : `+${value}h ahead`;

  const tickColor = value === 0 ? "#22c55e" : value < 0 ? "#a78bfa" : "#f97316";

  return (
    <div className="space-y-2 rounded-md border border-border bg-background/60 p-3 backdrop-blur">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLive((s) => !s)}
            className={`rounded px-2 py-0.5 text-[11px] font-bold transition-colors ${
              isLive
                ? "bg-green-600/20 text-green-400"
                : "bg-secondary text-muted-foreground hover:bg-secondary/80"
            }`}
          >
            {isLive ? "● LIVE" : "○ LIVE"}
          </button>
          <span className="font-mono text-muted-foreground">
            {target.toLocaleString()}
          </span>
        </div>
        <span className="font-semibold" style={{ color: tickColor }}>
          {label}
        </span>
      </div>
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
        className="h-1 w-full cursor-pointer appearance-none rounded-full bg-secondary [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
      />
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>-7 days</span>
        <span>Now</span>
        <span>+72h</span>
      </div>
    </div>
  );
}
