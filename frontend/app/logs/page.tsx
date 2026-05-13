"use client";

import { useState } from "react";
import { FileText, AlertTriangle, CheckCircle, XCircle, Filter, RefreshCw } from "lucide-react";
import { useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp } from "@/lib/utils";

type LogLevel = "all" | "error" | "warning" | "info";

export default function LogsPage() {
  const { data: statusData, isLoading, mutate } = useStatus();
  const [logLevel, setLogLevel] = useState<LogLevel>("all");

  const status = statusData?.data;

  // Combine warnings and errors from all sources
  const allLogs = [
    ...(status?.errors?.map((e) => ({ level: "error", message: e, source: "system" })) ?? []),
    ...(status?.warnings?.map((w) => ({ level: "warning", message: w, source: "system" })) ?? []),
    ...(status?.weather?.errors?.map((e) => ({ level: "error", message: e, source: "weather" })) ?? []),
    ...(status?.market?.errors?.map((e) => ({ level: "error", message: e, source: "market" })) ?? []),
    ...(status?.forecast?.errors?.map((e) => ({ level: "error", message: e, source: "forecast" })) ?? []),
    ...(status?.forecast?.mapping_warnings?.map((w) => ({ level: "warning", message: w, source: "forecast" })) ?? []),
    ...(status?.paper_trading?.errors?.map((e) => ({ level: "error", message: e, source: "paper_trading" })) ?? []),
    ...(status?.risk_gates?.blocked_reasons?.map((r) => ({ level: "warning", message: r, source: "risk_gates" })) ?? []),
  ];

  // Filter logs by level
  const filteredLogs = allLogs.filter((log) => {
    if (logLevel === "all") return true;
    return log.level === logLevel;
  });

  // Count by level
  const errorCount = allLogs.filter((l) => l.level === "error").length;
  const warningCount = allLogs.filter((l) => l.level === "warning").length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Logs & Artifacts</h1>
          <p className="text-muted-foreground">
            System logs, warnings, and error messages
          </p>
        </div>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-2 rounded-md bg-secondary px-4 py-2 text-sm text-secondary-foreground transition-colors hover:bg-secondary/80"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Log Summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-status-blocked/10">
                <XCircle className="h-6 w-6 text-status-blocked" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Errors</div>
                <div className="text-2xl font-bold text-status-blocked">
                  {errorCount}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-status-watch/10">
                <AlertTriangle className="h-6 w-6 text-status-watch" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Warnings</div>
                <div className="text-2xl font-bold text-status-watch">
                  {warningCount}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-status-ok/10">
                <CheckCircle className="h-6 w-6 text-status-ok" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">System Status</div>
                <div className="text-2xl font-bold text-foreground">
                  {status?.overall_status ?? "UNKNOWN"}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Health Checks */}
      <Card>
        <CardHeader>
          <CardTitle>Health Checks</CardTitle>
          <CardDescription>
            Status of each system component
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <HealthCheckItem
              name="Weather Data"
              status={status?.weather?.status ?? "UNKNOWN"}
              details={`Last update: ${formatTimestamp(status?.weather?.last_update)}`}
            />
            <HealthCheckItem
              name="Market Data"
              status={status?.market?.status ?? "UNKNOWN"}
              details={`${status?.market?.active_contracts ?? 0} active contracts`}
            />
            <HealthCheckItem
              name="Forecast Model"
              status={status?.forecast?.status ?? "UNKNOWN"}
              details={status?.forecast?.model_type ?? "N/A"}
            />
            <HealthCheckItem
              name="Risk Gates"
              status={status?.risk_gates?.status ?? "UNKNOWN"}
              details={`${status?.risk_gates?.gates_passed ?? 0}/${status?.risk_gates?.gates_total ?? 0} gates passed`}
            />
            <HealthCheckItem
              name="Paper Trading"
              status={status?.paper_trading?.status ?? "UNKNOWN"}
              details={status?.paper_trading?.signal_action ?? "N/A"}
            />
            <HealthCheckItem
              name="Overall"
              status={status?.overall_status ?? "UNKNOWN"}
              details={`Evidence: ${status?.evidence_classification ?? "N/A"}`}
            />
          </div>
        </CardContent>
      </Card>

      {/* Log Viewer */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Log Messages</CardTitle>
              <CardDescription>
                {filteredLogs.length} message(s) from current status
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={logLevel}
                onChange={(e) => setLogLevel(e.target.value as LogLevel)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All Levels</option>
                <option value="error">Errors Only</option>
                <option value="warning">Warnings Only</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredLogs.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              {allLogs.length === 0 
                ? "No log messages. System is operating normally."
                : "No messages match the selected filter."}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredLogs.map((log, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex items-start gap-3 rounded-lg border p-3",
                    log.level === "error" && "border-status-blocked/30 bg-status-blocked/5",
                    log.level === "warning" && "border-status-watch/30 bg-status-watch/5"
                  )}
                >
                  {log.level === "error" ? (
                    <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-status-blocked" />
                  ) : (
                    <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-status-watch" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "text-sm font-medium",
                        log.level === "error" ? "text-status-blocked" : "text-status-watch"
                      )}>
                        {log.level.toUpperCase()}
                      </span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                        {log.source}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-foreground">{log.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Artifacts Info */}
      <Card>
        <CardHeader>
          <CardTitle>Data Artifacts</CardTitle>
          <CardDescription>
            Location and status of backend data files
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <ArtifactRow
              name="Daily Status"
              path="backend/data/processed/status/kmia_daily_status_*.json"
              available={!!status}
            />
            <ArtifactRow
              name="Weather Snapshot"
              path="backend/data/processed/weather_nws/latest_nws_kmia_snapshot.json"
              available={status?.weather?.status === "OK"}
            />
            <ArtifactRow
              name="Market Snapshot"
              path="backend/data/processed/kalshi_market_snapshots/latest_kalshi_market_snapshot.json"
              available={status?.market?.status === "OK"}
            />
            <ArtifactRow
              name="Paper Signals"
              path="backend/data/processed/paper_trading/latest_paper_signal.json"
              available={status?.paper_trading?.signal_generated}
            />
            <ArtifactRow
              name="Paper Ledger"
              path="backend/data/processed/paper_trading/paper_trade_ledger.jsonl"
              available={true}
            />
            <ArtifactRow
              name="Calibration"
              path="backend/data/processed/aggregate_calibration/aggregate_calibration.json"
              available={false}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function HealthCheckItem({
  name,
  status,
  details,
}: {
  name: string;
  status: string;
  details: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted/50 p-4">
      <div>
        <div className="font-medium text-foreground">{name}</div>
        <div className="text-sm text-muted-foreground">{details}</div>
      </div>
      <StatusBadge status={status} size="sm" />
    </div>
  );
}

function ArtifactRow({
  name,
  path,
  available,
}: {
  name: string;
  path: string;
  available: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted/50 px-4 py-3">
      <div className="flex items-center gap-3">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <div>
          <div className="text-sm font-medium text-foreground">{name}</div>
          <div className="font-mono text-xs text-muted-foreground">{path}</div>
        </div>
      </div>
      <StatusBadge 
        status={available ? "OK" : "BLOCKED"} 
        size="sm" 
        showDot={false}
      />
    </div>
  );
}
