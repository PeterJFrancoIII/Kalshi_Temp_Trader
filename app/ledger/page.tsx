"use client";

import { BookOpen, DollarSign, TrendingUp, TrendingDown, AlertTriangle, Ban } from "lucide-react";
import { useLedger, useSignals, useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp, formatCurrency, formatPercentage } from "@/lib/utils";
import type { LedgerEntry } from "@/lib/types";

export default function LedgerPage() {
  const { data: ledgerData, isLoading: ledgerLoading } = useLedger();
  const { data: signalsData } = useSignals();
  const { data: statusData } = useStatus();

  const ledger = ledgerData?.data;
  const signals = signalsData?.data;
  const status = statusData?.data;

  if (ledgerLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading ledger data...</div>
      </div>
    );
  }

  const balance = ledger?.balance_cents ?? 0;
  const initialBalance = ledger?.initial_balance_cents ?? 10000000;
  const totalPnl = ledger?.total_pnl_cents ?? 0;
  const pnlPercent = initialBalance > 0 ? totalPnl / initialBalance : 0;

  const openPositions = ledger?.open_positions ?? [];
  const settledPositions = ledger?.settled_positions ?? [];
  const allEntries = ledger?.entries ?? [];

  // Check if trades were blocked
  const blockedCandidates = signals?.blocked_candidates ?? [];
  const hasBlockedTrades = blockedCandidates.length > 0 && signals?.signal_action === "BLOCKED_BY_RISK";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Paper Ledger</h1>
          <p className="text-muted-foreground">
            Track paper trading positions and performance
          </p>
        </div>
        <StatusBadge status={status?.paper_trading?.status ?? "OK"} size="lg" />
      </div>

      {/* DRY-RUN Banner */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <div>
            <h3 className="font-medium text-amber-500">Paper Trading Only</h3>
            <p className="text-sm text-amber-500/80">
              This ledger tracks simulated positions. No real orders are placed or executed.
            </p>
          </div>
        </div>
      </div>

      {/* Blocked Trades Notice */}
      {hasBlockedTrades && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <Ban className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">No Trades Placed</h3>
              <p className="text-sm text-status-watch/80">
                Risk gates blocked all {blockedCandidates.length} signal candidate(s).
                No paper positions were opened.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Account Summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <DollarSign className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Current Balance</div>
                <div className="text-2xl font-bold text-foreground">
                  {formatCurrency(balance)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                <BookOpen className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Initial Balance</div>
                <div className="text-2xl font-bold text-foreground">
                  {formatCurrency(initialBalance)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className={cn(
                "flex h-12 w-12 items-center justify-center rounded-lg",
                totalPnl >= 0 ? "bg-status-ok/10" : "bg-status-blocked/10"
              )}>
                {totalPnl >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-status-ok" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-status-blocked" />
                )}
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total PnL</div>
                <div className={cn(
                  "text-2xl font-bold",
                  totalPnl >= 0 ? "text-status-ok" : "text-status-blocked"
                )}>
                  {totalPnl >= 0 ? "+" : ""}{formatCurrency(totalPnl)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className={cn(
                "flex h-12 w-12 items-center justify-center rounded-lg",
                pnlPercent >= 0 ? "bg-status-ok/10" : "bg-status-blocked/10"
              )}>
                {pnlPercent >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-status-ok" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-status-blocked" />
                )}
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Return</div>
                <div className={cn(
                  "text-2xl font-bold",
                  pnlPercent >= 0 ? "text-status-ok" : "text-status-blocked"
                )}>
                  {pnlPercent >= 0 ? "+" : ""}{formatPercentage(pnlPercent, 2)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Open Positions */}
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <CardDescription>
            {openPositions.length === 0 
              ? "No open paper positions"
              : `${openPositions.length} position(s) currently open`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {openPositions.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No open positions. All candidates may have been blocked by risk gates.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Contract
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Side
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Quantity
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Entry Price
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Cost
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Opened At
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.map((entry, i) => (
                    <PositionRow key={i} entry={entry} showSettlement={false} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Settled Positions */}
      <Card>
        <CardHeader>
          <CardTitle>Settled Positions</CardTitle>
          <CardDescription>
            {settledPositions.length === 0 
              ? "No settled positions yet"
              : `${settledPositions.length} position(s) have settled`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {settledPositions.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No positions have settled yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Contract
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Side
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Quantity
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Entry
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Settlement
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      PnL
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Settled At
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {settledPositions.map((entry, i) => (
                    <PositionRow key={i} entry={entry} showSettlement={true} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Full Transaction History */}
      {allEntries.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Transaction History</CardTitle>
            <CardDescription>
              Complete ledger of all paper trading activity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Timestamp
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Contract
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Side
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Qty
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Price
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      PnL
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {allEntries.slice().reverse().map((entry, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/50 hover:bg-muted/50"
                    >
                      <td className="px-4 py-2 text-sm text-muted-foreground">
                        {formatTimestamp(entry.timestamp)}
                      </td>
                      <td className="px-4 py-2">
                        <StatusBadge
                          status={entry.entry_type === "BLOCKED" ? "BLOCKED" : "OK"}
                          size="sm"
                          showDot={false}
                        />
                      </td>
                      <td className="px-4 py-2 font-mono text-sm text-foreground">
                        {entry.contract_ticker}
                      </td>
                      <td className={cn(
                        "px-4 py-2 text-sm font-medium",
                        entry.side === "YES" ? "text-status-ok" : "text-status-blocked"
                      )}>
                        {entry.side}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm text-foreground">
                        {entry.quantity}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm text-foreground">
                        {formatCurrency(entry.price_cents)}
                      </td>
                      <td className={cn(
                        "px-4 py-2 text-right font-mono text-sm",
                        entry.pnl_cents == null 
                          ? "text-muted-foreground"
                          : entry.pnl_cents >= 0 
                            ? "text-status-ok"
                            : "text-status-blocked"
                      )}>
                        {entry.pnl_cents != null 
                          ? `${entry.pnl_cents >= 0 ? "+" : ""}${formatCurrency(entry.pnl_cents)}`
                          : "—"}
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
        title="Ledger Data Freshness"
        description="Time since last ledger update"
        timestamp={ledgerData?.timestamp}
      />
    </div>
  );
}

function PositionRow({ 
  entry, 
  showSettlement 
}: { 
  entry: LedgerEntry; 
  showSettlement: boolean;
}) {
  return (
    <tr className="border-b border-border/50 hover:bg-muted/50">
      <td className="px-4 py-3 font-mono text-sm text-foreground">
        {entry.contract_ticker}
      </td>
      <td className={cn(
        "px-4 py-3 text-sm font-medium",
        entry.side === "YES" ? "text-status-ok" : "text-status-blocked"
      )}>
        {entry.side}
      </td>
      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
        {entry.quantity}
      </td>
      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
        {formatCurrency(entry.price_cents)}
      </td>
      {showSettlement ? (
        <>
          <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
            {entry.settlement_price_cents != null 
              ? formatCurrency(entry.settlement_price_cents)
              : "—"}
          </td>
          <td className={cn(
            "px-4 py-3 text-right font-mono text-sm font-medium",
            entry.pnl_cents == null 
              ? "text-muted-foreground"
              : entry.pnl_cents >= 0 
                ? "text-status-ok"
                : "text-status-blocked"
          )}>
            {entry.pnl_cents != null 
              ? `${entry.pnl_cents >= 0 ? "+" : ""}${formatCurrency(entry.pnl_cents)}`
              : "—"}
          </td>
        </>
      ) : (
        <td className="px-4 py-3 text-right font-mono text-sm text-muted-foreground">
          {formatCurrency(entry.price_cents * entry.quantity)}
        </td>
      )}
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {formatTimestamp(entry.timestamp)}
      </td>
    </tr>
  );
}
