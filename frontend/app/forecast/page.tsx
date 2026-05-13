"use client";

import { useMemo } from "react";
import { BarChart3, AlertTriangle, Info } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";
import { useForecast, useMarkets, useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp, formatPercentage } from "@/lib/utils";

export default function ForecastPage() {
  const { data: forecastData, isLoading: forecastLoading } = useForecast();
  const { data: marketsData } = useMarkets();
  const { data: statusData } = useStatus();

  const forecast = forecastData?.data;
  const markets = marketsData?.data;
  const status = statusData?.data;
  const forecastStatus = status?.forecast;

  // Parse distribution data for chart
  const chartData = useMemo(() => {
    if (!forecast?.probabilities) return [];
    
    return Object.entries(forecast.probabilities)
      .map(([temp, prob]) => ({
        temperature: parseInt(temp, 10),
        probability: prob as number,
        label: `${temp}°F`,
      }))
      .filter((d) => !isNaN(d.temperature))
      .sort((a, b) => a.temperature - b.temperature);
  }, [forecast?.probabilities]);

  // Calculate cumulative probabilities
  const tableData = useMemo(() => {
    if (!forecast?.probabilities) return [];
    
    let cumulative = 0;
    return Object.entries(forecast.probabilities)
      .map(([temp, prob]) => ({
        temperature: parseInt(temp, 10),
        probability: prob as number,
      }))
      .filter((d) => !isNaN(d.temperature))
      .sort((a, b) => a.temperature - b.temperature)
      .map((d) => {
        cumulative += d.probability;
        return {
          ...d,
          cumulative,
        };
      });
  }, [forecast?.probabilities]);

  // Find temperature ranges that map to contracts
  const contractRanges = useMemo(() => {
    if (!markets?.contracts) return [];
    
    return markets.contracts
      .filter((c) => c.floor_strike != null && c.cap_strike != null)
      .map((c) => ({
        ticker: c.ticker,
        title: c.title,
        floor: c.floor_strike!,
        cap: c.cap_strike!,
        marketProb: c.last_price ? c.last_price / 100 : null,
      }));
  }, [markets?.contracts]);

  // Calculate model probability for each contract range
  const mappingData = useMemo(() => {
    if (!forecast?.probabilities || !contractRanges.length) return [];

    return contractRanges.map((range) => {
      let modelProb = 0;
      for (const [temp, prob] of Object.entries(forecast.probabilities)) {
        const t = parseInt(temp, 10);
        if (t >= range.floor && t < range.cap) {
          modelProb += prob as number;
        }
      }
      return {
        ...range,
        modelProb,
        edge: range.marketProb != null ? modelProb - range.marketProb : null,
      };
    });
  }, [forecast?.probabilities, contractRanges]);

  // Check distribution sum
  const distributionSum = chartData.reduce((sum, d) => sum + d.probability, 0);
  const isValidSum = Math.abs(distributionSum - 1) < 0.01;

  if (forecastLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading forecast data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Forecast Distribution</h1>
          <p className="text-muted-foreground">
            Integer temperature probability forecast for KMIA
          </p>
        </div>
        <StatusBadge status={forecastStatus?.status ?? "UNKNOWN"} size="lg" />
      </div>

      {/* Warnings */}
      {forecastStatus?.mapping_warnings && forecastStatus.mapping_warnings.length > 0 && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">Mapping Warnings</h3>
              <ul className="mt-1 space-y-1">
                {forecastStatus.mapping_warnings.map((warning, i) => (
                  <li key={i} className="text-sm text-status-watch/80">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Distribution Sum Warning */}
      {chartData.length > 0 && !isValidSum && (
        <div className="rounded-lg border border-status-blocked/30 bg-status-blocked/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-blocked" />
            <div>
              <h3 className="font-medium text-status-blocked">Invalid Distribution</h3>
              <p className="text-sm text-status-blocked/80">
                Probabilities sum to {formatPercentage(distributionSum)} instead of 100%.
                This may indicate an incomplete or corrupted forecast.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Missing Data Warning */}
      {forecastData?.missing && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">Data Unavailable</h3>
              <p className="text-sm text-status-watch/80">
                {forecastData.error || "Forecast data file not found. The backend may not have run yet."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Forecast Summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Model Type</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {forecast?.model_type ?? forecastStatus?.model_type ?? "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Target Date</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {forecast?.target_date ?? status?.target_date ?? "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Distribution Sum</div>
            <div className={cn(
              "mt-1 text-lg font-bold",
              isValidSum ? "text-status-ok" : "text-status-blocked"
            )}>
              {formatPercentage(distributionSum)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Temperature Range</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {chartData.length > 0 
                ? `${chartData[0].temperature}°F - ${chartData[chartData.length - 1].temperature}°F`
                : "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Distribution Chart */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Temperature Probability Distribution</CardTitle>
            <CardDescription>
              Probability of high temperature reaching each integer value
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <XAxis 
                    dataKey="label" 
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                    interval={1}
                  />
                  <YAxis 
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const data = payload[0].payload;
                      return (
                        <div className="rounded-lg border border-border bg-card p-3 shadow-lg">
                          <div className="font-medium text-foreground">{data.label}</div>
                          <div className="text-sm text-muted-foreground">
                            Probability: {formatPercentage(data.probability, 2)}
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="probability" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          entry.temperature >= 85 && entry.temperature <= 92
                            ? "hsl(var(--primary))"
                            : "hsl(var(--muted-foreground))"
                        }
                        fillOpacity={
                          entry.temperature >= 85 && entry.temperature <= 92 ? 1 : 0.3
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded bg-primary" />
                <span>Typical trading range (85-92°F)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded bg-muted-foreground/30" />
                <span>Other temperatures</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Model-to-Contract Mapping */}
      {mappingData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Model-to-Contract Mapping</CardTitle>
            <CardDescription>
              Comparison of model probabilities vs market prices for each contract range
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Contract
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Range
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Model Prob
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Market Prob
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Edge
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {mappingData.map((row) => (
                    <tr
                      key={row.ticker}
                      className="border-b border-border/50 hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 font-mono text-sm text-foreground">
                        {row.ticker}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {row.floor}°F - {row.cap}°F
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {formatPercentage(row.modelProb, 1)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {row.marketProb != null ? formatPercentage(row.marketProb, 1) : "N/A"}
                      </td>
                      <td className={cn(
                        "px-4 py-3 text-right font-mono text-sm",
                        row.edge == null 
                          ? "text-muted-foreground"
                          : row.edge > 0.05 
                            ? "text-status-ok font-medium"
                            : row.edge < -0.05 
                              ? "text-status-blocked"
                              : "text-foreground"
                      )}>
                        {row.edge != null 
                          ? `${row.edge > 0 ? "+" : ""}${formatPercentage(row.edge, 1)}`
                          : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Probability Table */}
      {tableData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Detailed Distribution Table</CardTitle>
            <CardDescription>
              Individual and cumulative probabilities for each temperature
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Temperature
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Probability
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Cumulative
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {tableData.map((row) => (
                    <tr
                      key={row.temperature}
                      className={cn(
                        "border-b border-border/50",
                        row.temperature >= 85 && row.temperature <= 92 && "bg-primary/5"
                      )}
                    >
                      <td className="px-4 py-2 text-sm text-foreground">
                        {row.temperature}°F
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm text-foreground">
                        {formatPercentage(row.probability, 2)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm text-muted-foreground">
                        {formatPercentage(row.cumulative, 2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Freshness */}
      <FreshnessCard
        title="Forecast Data Freshness"
        description="Time since last forecast generation"
        timestamp={forecast?.timestamp}
      />
    </div>
  );
}
