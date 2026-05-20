import { cn } from "@/lib/utils";

interface RiskGaugeProps {
  value: number; // 0–100
  label: string;
  thresholds?: { low: number; moderate: number }; // defaults: low=30, moderate=70
  className?: string;
}

export default function RiskGauge({
  value,
  label,
  thresholds = { low: 30, moderate: 70 },
  className,
}: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const tier =
    clamped < thresholds.low ? "low" : clamped < thresholds.moderate ? "moderate" : "high";
  const tierColors = {
    low: { bar: "bg-green-500", text: "text-green-400" },
    moderate: { bar: "bg-yellow-500", text: "text-yellow-400" },
    high: { bar: "bg-red-500", text: "text-red-400" },
  };
  const colors = tierColors[tier];

  return (
    <div className={cn("rounded-lg border bg-card p-4", className)}>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span className={cn("text-sm font-bold", colors.text)}>
          {clamped.toFixed(0)} — {tier.toUpperCase()}
        </span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-secondary">
        <div
          className={cn("h-full rounded-full transition-all duration-500", colors.bar)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
