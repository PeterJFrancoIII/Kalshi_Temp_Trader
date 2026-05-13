import { cn } from "@/lib/utils";
import type { OverallStatus, GateResult } from "@/lib/types";

interface StatusBadgeProps {
  status: OverallStatus | GateResult | string;
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
}

const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
  // Overall status
  OK: { bg: "bg-status-ok/10", text: "text-status-ok", dot: "bg-status-ok" },
  WATCH: { bg: "bg-status-watch/10", text: "text-status-watch", dot: "bg-status-watch" },
  BLOCKED: { bg: "bg-status-blocked/10", text: "text-status-blocked", dot: "bg-status-blocked" },
  INVALID: { bg: "bg-status-invalid/10", text: "text-status-invalid", dot: "bg-status-invalid" },
  
  // Gate results
  PASS: { bg: "bg-status-ok/10", text: "text-status-ok", dot: "bg-status-ok" },
  FAIL: { bg: "bg-status-blocked/10", text: "text-status-blocked", dot: "bg-status-blocked" },
  SKIP: { bg: "bg-muted", text: "text-muted-foreground", dot: "bg-muted-foreground" },
  
  // Freshness
  FRESH: { bg: "bg-status-ok/10", text: "text-status-ok", dot: "bg-status-ok" },
  STALE: { bg: "bg-status-blocked/10", text: "text-status-blocked", dot: "bg-status-blocked" },
  WARNING: { bg: "bg-status-watch/10", text: "text-status-watch", dot: "bg-status-watch" },
  
  // Default
  UNKNOWN: { bg: "bg-muted", text: "text-muted-foreground", dot: "bg-muted-foreground" },
};

const sizeClasses = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3 py-1.5 text-sm",
};

const dotSizeClasses = {
  sm: "h-1.5 w-1.5",
  md: "h-2 w-2",
  lg: "h-2.5 w-2.5",
};

export function StatusBadge({ status, size = "md", showDot = true }: StatusBadgeProps) {
  const colors = statusColors[status] || statusColors.UNKNOWN;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md font-medium",
        colors.bg,
        colors.text,
        sizeClasses[size]
      )}
    >
      {showDot && (
        <span className={cn("rounded-full", colors.dot, dotSizeClasses[size])} />
      )}
      {status}
    </span>
  );
}
