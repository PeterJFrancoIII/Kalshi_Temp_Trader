import { cn, formatTimestamp, getTimestampAge, getFreshnessStatus } from "@/lib/utils";
import { Clock, AlertCircle, CheckCircle, AlertTriangle } from "lucide-react";

interface FreshnessCardProps {
  title: string;
  description?: string;
  timestamp: string | null | undefined;
  thresholds?: { fresh: number; stale: number };
  children?: React.ReactNode;
}

// Default thresholds: fresh < 5 min, stale > 15 min
const DEFAULT_THRESHOLDS = {
  fresh: 5 * 60 * 1000, // 5 minutes
  stale: 15 * 60 * 1000, // 15 minutes
};

export function FreshnessCard({
  title,
  description,
  timestamp,
  thresholds = DEFAULT_THRESHOLDS,
  children,
}: FreshnessCardProps) {
  const ageMs = getTimestampAge(timestamp);
  const freshness = getFreshnessStatus(ageMs, thresholds);

  const getAgeText = () => {
    if (ageMs === null) return "Unknown";
    const minutes = Math.floor(ageMs / 60000);
    if (minutes < 1) return "< 1 min ago";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const FreshnessIcon = {
    fresh: CheckCircle,
    warning: AlertTriangle,
    stale: AlertCircle,
    unknown: Clock,
  }[freshness];

  const freshnessColors = {
    fresh: "text-status-ok",
    warning: "text-status-watch",
    stale: "text-status-blocked",
    unknown: "text-muted-foreground",
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
        <FreshnessIcon
          className={cn("h-5 w-5", freshnessColors[freshness])}
        />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          {formatTimestamp(timestamp)}
        </span>
      </div>

      <div className="mt-1 flex items-center gap-2">
        <span
          className={cn(
            "text-sm font-medium",
            freshnessColors[freshness]
          )}
        >
          {getAgeText()}
        </span>
        <span
          className={cn(
            "rounded px-1.5 py-0.5 text-xs font-medium uppercase",
            freshness === "fresh" && "bg-status-ok/10 text-status-ok",
            freshness === "warning" && "bg-status-watch/10 text-status-watch",
            freshness === "stale" && "bg-status-blocked/10 text-status-blocked",
            freshness === "unknown" && "bg-muted text-muted-foreground"
          )}
        >
          {freshness}
        </span>
      </div>

      {children && <div className="mt-3 border-t border-border pt-3">{children}</div>}
    </div>
  );
}
