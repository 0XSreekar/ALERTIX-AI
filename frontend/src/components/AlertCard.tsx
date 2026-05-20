import type { Alert } from "@/lib/types";
import { SEVERITY_COLORS } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface AlertCardProps {
  alert: Alert;
  onClick?: () => void;
}

export default function AlertCard({ alert, onClick }: AlertCardProps) {
  const borderColor = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info;

  return (
    <Card
      className="cursor-pointer transition-colors hover:bg-accent/50"
      style={{ borderLeftWidth: 4, borderLeftColor: borderColor }}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <span
            className="rounded px-2 py-0.5 text-xs font-semibold uppercase"
            style={{ backgroundColor: borderColor + "20", color: borderColor }}
          >
            {alert.severity}
          </span>
          <span className="text-xs text-muted-foreground">
            {new Date(alert.created_at).toLocaleString()}
          </span>
        </div>
        <CardTitle className="text-base">{alert.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {alert.explanation ? (
          <p className="text-sm text-muted-foreground">{alert.explanation}</p>
        ) : (
          <p className="text-sm italic text-muted-foreground">
            Explanation {alert.explanation_status === "pending" ? "pending..." : "unavailable"}
          </p>
        )}
        {alert.probability != null && (
          <p className="mt-1 text-xs text-muted-foreground">
            Probability: {(alert.probability * 100).toFixed(0)}%
          </p>
        )}
      </CardContent>
    </Card>
  );
}
