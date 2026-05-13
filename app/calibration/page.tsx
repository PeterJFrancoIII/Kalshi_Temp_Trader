"use client";

import { useMemo } from "react";
import { Target, CheckCircle, XCircle, AlertTriangle, Calendar } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts";
import { useCalibration, useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp, formatPercentage } from "@/lib/utils";

export default function CalibrationPage() {
  const { data: calibrationData, isLoading: calibrationLoading } = useCalibration();
  const { data: statusData } = useStatus();

  const calibration = calibrationData?.data;
  const status = statusData?.data;

  // Parse bucket data for chart
  const bucketData = useMemo(() => {
    if (!calibration?.by_bucket) return [];
    
    return Object.entries(calibration.by_bucket)
      .map(([bucket, data]) => ({
        bucket,
        count: (data as { count: number; correct: number; accuracy: number }).count,
        correct: (data as { count: number; correct: number; accuracy: number }).correct,
        accuracy: (data as { count: number; correct: number; accuracy: number }).accuracy,
      }))
      .sort((a, b) => a.bucket.localeCompare(b.bucket));
  }, [calibration?.by_bucket]);

  if (calibrationLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading calibration data...</div>
      </div>
    );
  }

  const totalSettlements = calibration?.total_settlements ?? 0;
  const correctSettlements = calibration?.correct_settlements ?? 0;
  const accuracy = calibration?.accuracy ?? 0;
  const excludedDays = calibration?.excluded_days ?? [];

  // Determine accuracy status
  const accuracyStatus = accuracy >= 0.6 ? "OK" : accuracy >= 0.4 ? "WATCH" : "BLOCKED";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Calibration & Backtests</h1>
          <p className="text-muted-foreground">
            Model accuracy and historical performance analysis
          </p>
        </div>
        <StatusBadge status={accuracyStatus} size="lg" />
      </div>

      {/* Missing Data Warning */}
      {calibrationData?.missing && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">Data Unavailable</h3>
              <p className="text-sm text-status-watch/80">
                {calibrationData.error || "Calibration data file not found. Run the calibration script to generate data."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Target className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Overall Accuracy</div>
                <div className={cn(
                  "text-2xl font-bold",
                  accuracy >= 0.6 ? "text-status-ok" : accuracy >= 0.4 ? "text-status-watch" : "text-status-blocked"
                )}>
                  {formatPercentage(accuracy, 1)}
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
                <div className="text-sm text-muted-foreground">Correct Predictions</div>
                <div className="text-2xl font-bold text-foreground">
                  {correctSettlements}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                <Calendar className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total Settlements</div>
                <div className="text-2xl font-bold text-foreground">
                  {totalSettlements}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-status-watch/10">
                <XCircle className="h-6 w-6 text-status-watch" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Excluded Days</div>
                <div className="text-2xl font-bold text-foreground">
                  {excludedDays.length}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Accuracy by Bucket Chart */}
      {bucketData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Accuracy by Probability Bucket</CardTitle>
            <CardDescription>
              Model accuracy grouped by predicted probability ranges
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bucketData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <XAxis 
                    dataKey="bucket" 
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                  />
                  <YAxis 
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                    domain={[0, 1]}
                  />
                  <ReferenceLine 
                    y={0.5} 
                    stroke="hsl(var(--muted-foreground))" 
                    strokeDasharray="3 3"
                    label={{ value: "50% baseline", position: "right", fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const data = payload[0].payload;
                      return (
                        <div className="rounded-lg border border-border bg-card p-3 shadow-lg">
                          <div className="font-medium text-foreground">{data.bucket}</div>
                          <div className="text-sm text-muted-foreground">
                            Accuracy: {formatPercentage(data.accuracy, 1)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {data.correct} / {data.count} correct
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                    {bucketData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          entry.accuracy >= 0.6
                            ? "hsl(var(--status-ok))"
                            : entry.accuracy >= 0.4
                              ? "hsl(var(--status-watch))"
                              : "hsl(var(--status-blocked))"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bucket Details Table */}
      {bucketData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Calibration Details by Bucket</CardTitle>
            <CardDescription>
              Detailed breakdown of predictions and outcomes per probability bucket
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Bucket
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Total
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Correct
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Accuracy
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {bucketData.map((bucket) => (
                    <tr
                      key={bucket.bucket}
                      className="border-b border-border/50 hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 font-mono text-sm text-foreground">
                        {bucket.bucket}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {bucket.count}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {bucket.correct}
                      </td>
                      <td className={cn(
                        "px-4 py-3 text-right font-mono text-sm font-medium",
                        bucket.accuracy >= 0.6 
                          ? "text-status-ok" 
                          : bucket.accuracy >= 0.4 
                            ? "text-status-watch" 
                            : "text-status-blocked"
                      )}>
                        {formatPercentage(bucket.accuracy, 1)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={
                            bucket.accuracy >= 0.6 
                              ? "OK" 
                              : bucket.accuracy >= 0.4 
                                ? "WATCH" 
                                : "BLOCKED"
                          }
                          size="sm"
                          showDot={false}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Excluded Days */}
      {excludedDays.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Excluded Days</CardTitle>
            <CardDescription>
              Days excluded from calibration due to data issues or anomalies
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {excludedDays.map((day, i) => (
                <span
                  key={i}
                  className="rounded-md border border-border bg-muted px-3 py-1 font-mono text-sm text-muted-foreground"
                >
                  {day}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Backtest Report Status */}
      <Card>
        <CardHeader>
          <CardTitle>Backtest Reports</CardTitle>
          <CardDescription>
            Historical backtesting results and performance analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-status-watch" />
              <div>
                <h3 className="font-medium text-status-watch">No Backtest Report Found</h3>
                <p className="text-sm text-status-watch/80">
                  Backtest reports are generated separately. Check the backend logs for backtest execution status.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Freshness */}
      <FreshnessCard
        title="Calibration Data Freshness"
        description="Time since last calibration run"
        timestamp={calibration?.timestamp}
        thresholds={{ fresh: 24 * 60 * 60 * 1000, stale: 7 * 24 * 60 * 60 * 1000 }} // 1 day fresh, 1 week stale
      />
    </div>
  );
}
