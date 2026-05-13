import { cn } from "@/lib/utils";
import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import type { EvidenceClassification } from "@/lib/types";

interface EvidenceBadgeProps {
  classification: EvidenceClassification | string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

const classificationConfig: Record<
  string,
  { bg: string; text: string; icon: typeof CheckCircle; label: string }
> = {
  VALID_PAPER_EVAL: {
    bg: "bg-status-ok/10 border-status-ok/30",
    text: "text-status-ok",
    icon: CheckCircle,
    label: "Valid Paper Eval",
  },
  SAFETY_ONLY: {
    bg: "bg-status-watch/10 border-status-watch/30",
    text: "text-status-watch",
    icon: AlertTriangle,
    label: "Safety Only",
  },
  INVALID: {
    bg: "bg-status-blocked/10 border-status-blocked/30",
    text: "text-status-blocked",
    icon: XCircle,
    label: "Invalid",
  },
  UNKNOWN: {
    bg: "bg-muted border-border",
    text: "text-muted-foreground",
    icon: AlertTriangle,
    label: "Unknown",
  },
};

const sizeClasses = {
  sm: "px-2 py-0.5 text-xs gap-1",
  md: "px-3 py-1 text-sm gap-1.5",
  lg: "px-4 py-1.5 text-sm gap-2",
};

const iconSizeClasses = {
  sm: "h-3 w-3",
  md: "h-4 w-4",
  lg: "h-5 w-5",
};

export function EvidenceBadge({
  classification,
  size = "md",
  showIcon = true,
}: EvidenceBadgeProps) {
  const config = classificationConfig[classification] || classificationConfig.UNKNOWN;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border font-medium",
        config.bg,
        config.text,
        sizeClasses[size]
      )}
    >
      {showIcon && <Icon className={iconSizeClasses[size]} />}
      {config.label}
    </span>
  );
}
