"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import useSWR from "swr";
import { cn } from "@/lib/utils";
import type { ApiResponse, DailyStatus } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export function Header() {
  const { data, isLoading, mutate } = useSWR<ApiResponse<DailyStatus>>(
    "/api/status",
    fetcher,
    { refreshInterval: 30000 }
  );

  const status = data?.data;
  const overallStatus = status?.overall_status ?? "UNKNOWN";
  const evidenceClass = status?.evidence_classification ?? "UNKNOWN";

  return (
    <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-foreground">
          KMIA Temperature Trading
        </h1>
        
        {/* DRY-RUN Badge - Always visible */}
        <div className="flex items-center gap-2 rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-1">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <span className="text-sm font-medium text-amber-500">
            DRY-RUN / PAPER EVALUATION ONLY
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Overall Status Badge */}
        <div
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1 text-sm font-medium",
            overallStatus === "OK" && "bg-status-ok/10 text-status-ok",
            overallStatus === "WATCH" && "bg-status-watch/10 text-status-watch",
            overallStatus === "BLOCKED" && "bg-status-blocked/10 text-status-blocked",
            overallStatus === "INVALID" && "bg-status-invalid/10 text-status-invalid",
            overallStatus === "UNKNOWN" && "bg-muted text-muted-foreground"
          )}
        >
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              overallStatus === "OK" && "bg-status-ok",
              overallStatus === "WATCH" && "bg-status-watch",
              overallStatus === "BLOCKED" && "bg-status-blocked",
              overallStatus === "INVALID" && "bg-status-invalid",
              overallStatus === "UNKNOWN" && "bg-muted-foreground"
            )}
          />
          {isLoading ? "Loading..." : overallStatus}
        </div>

        {/* Evidence Classification Badge */}
        <div
          className={cn(
            "rounded-md px-3 py-1 text-sm font-medium",
            evidenceClass === "VALID_PAPER_EVAL" && "bg-status-ok/10 text-status-ok",
            evidenceClass === "SAFETY_ONLY" && "bg-status-watch/10 text-status-watch",
            evidenceClass === "INVALID" && "bg-status-blocked/10 text-status-blocked",
            evidenceClass === "UNKNOWN" && "bg-muted text-muted-foreground"
          )}
        >
          {evidenceClass}
        </div>

        {/* Refresh Button */}
        <button
          onClick={() => mutate()}
          className="flex items-center gap-2 rounded-md bg-secondary px-3 py-1.5 text-sm text-secondary-foreground transition-colors hover:bg-secondary/80"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          Refresh
        </button>
      </div>
    </header>
  );
}
