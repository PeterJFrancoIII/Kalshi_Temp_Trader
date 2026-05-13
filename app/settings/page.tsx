"use client";

import { Settings, Info, AlertTriangle, Lock, GitBranch, Clock } from "lucide-react";
import { useStatus } from "@/hooks/use-data";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { formatTimestamp } from "@/lib/utils";

export default function SettingsPage() {
  const { data: statusData } = useStatus();
  const status = statusData?.data;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground">
            System configuration and environment information
          </p>
        </div>
      </div>

      {/* Read-Only Notice */}
      <div className="rounded-lg border border-primary/30 bg-primary/10 p-4">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-5 w-5 text-primary" />
          <div>
            <h3 className="font-medium text-primary">Read-Only Dashboard</h3>
            <p className="text-sm text-primary/80">
              This dashboard displays system settings but does not allow modifications.
              Configuration changes must be made through the backend.
            </p>
          </div>
        </div>
      </div>

      {/* Paper Trading Disclaimer */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-500" />
          <div>
            <h3 className="font-medium text-amber-500">Paper Trading Mode</h3>
            <p className="text-sm text-amber-500/80">
              This system operates in paper trading mode only. No real orders are placed,
              no real money is at risk, and no actual trading is executed. All positions
              and PnL are simulated for evaluation purposes.
            </p>
          </div>
        </div>
      </div>

      {/* System Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-primary" />
            <CardTitle>System Information</CardTitle>
          </div>
          <CardDescription>
            Current system configuration and status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Target Date</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.target_date ?? "N/A"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Last Status Update</div>
              <div className="mt-1 font-medium text-foreground">
                {formatTimestamp(status?.timestamp)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Overall Status</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.overall_status ?? "UNKNOWN"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Evidence Classification</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.evidence_classification ?? "UNKNOWN"}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Weather Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Weather Configuration</CardTitle>
          <CardDescription>
            NWS weather data source settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Station ID</div>
              <div className="mt-1 font-mono font-medium text-foreground">KMIA</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Data Source</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.weather?.source ?? "National Weather Service"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Status</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.weather?.status ?? "UNKNOWN"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Last Update</div>
              <div className="mt-1 font-medium text-foreground">
                {formatTimestamp(status?.weather?.last_update)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Market Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Market Configuration</CardTitle>
          <CardDescription>
            Kalshi market data settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Event Ticker</div>
              <div className="mt-1 font-mono font-medium text-foreground">
                {status?.market?.event_ticker ?? "N/A"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Series Ticker</div>
              <div className="mt-1 font-mono font-medium text-foreground">
                {status?.market?.series_ticker ?? "N/A"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Active Contracts</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.market?.active_contracts ?? 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Orderbook Freshness</div>
              <div className="mt-1 font-medium text-foreground">
                {formatTimestamp(status?.market?.orderbook_freshness)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Forecast Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Forecast Configuration</CardTitle>
          <CardDescription>
            Temperature forecast model settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Model Type</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.forecast?.model_type ?? "N/A"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Distribution Sum</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.forecast?.distribution_sum != null 
                  ? `${(status.forecast.distribution_sum * 100).toFixed(2)}%`
                  : "N/A"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Status</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.forecast?.status ?? "UNKNOWN"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Mapping Warnings</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.forecast?.mapping_warnings?.length ?? 0}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Gates Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Gates Configuration</CardTitle>
          <CardDescription>
            Trading risk management settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Gates Passed</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.risk_gates?.gates_passed ?? 0} / {status?.risk_gates?.gates_total ?? 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Status</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.risk_gates?.status ?? "UNKNOWN"}
              </div>
            </div>
          </div>
          {status?.risk_gates?.blocked_reasons && status.risk_gates.blocked_reasons.length > 0 && (
            <div className="mt-4">
              <div className="text-sm text-muted-foreground">Blocked Reasons</div>
              <ul className="mt-2 space-y-1">
                {status.risk_gates.blocked_reasons.map((reason, i) => (
                  <li key={i} className="text-sm text-status-watch">
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Paper Trading Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Paper Trading Configuration</CardTitle>
          <CardDescription>
            Simulated trading settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground">Signal Generated</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.paper_trading?.signal_generated ? "Yes" : "No"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Signal Action</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.paper_trading?.signal_action ?? "NO_SIGNAL"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Paper Balance</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.paper_trading?.paper_balance_cents != null 
                  ? `$${(status.paper_trading.paper_balance_cents / 100).toFixed(2)}`
                  : "N/A"}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Status</div>
              <div className="mt-1 font-medium text-foreground">
                {status?.paper_trading?.status ?? "UNKNOWN"}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Security Notice */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-primary" />
            <CardTitle>Security & Access</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 p-4">
              <Lock className="mt-0.5 h-5 w-5 text-muted-foreground" />
              <div>
                <div className="font-medium text-foreground">No Trading Controls</div>
                <div className="text-sm text-muted-foreground">
                  This dashboard does not include any buttons or controls to place orders.
                  All trading functionality is handled by the backend system.
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 p-4">
              <GitBranch className="mt-0.5 h-5 w-5 text-muted-foreground" />
              <div>
                <div className="font-medium text-foreground">Data Source</div>
                <div className="text-sm text-muted-foreground">
                  All data is read directly from backend JSON artifacts.
                  No modifications are made to the backend data.
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 p-4">
              <Clock className="mt-0.5 h-5 w-5 text-muted-foreground" />
              <div>
                <div className="font-medium text-foreground">Auto-Refresh</div>
                <div className="text-sm text-muted-foreground">
                  Data is automatically refreshed every 30 seconds to keep the dashboard current.
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
