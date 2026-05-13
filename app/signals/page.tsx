"use client";

import { AlertCircle, Shield, CheckCircle, XCircle, AlertTriangle, Ban } from "lucide-react";
import { useSignals, useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { EvidenceBadge } from "@/components/dashboard/evidence-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp, formatPercentage } from "@/lib/utils";
import type { SignalCandidate, RiskGate } from "@/lib/types";

export default function SignalsPage() {
  const { data: signalsData, isLoading: signalsLoading } = useSignals();
  const { data: statusData } = useStatus();

  const signals = signalsData?.data;
  const status = statusData?.data;
  const riskStatus = status?.risk_gates;

  if (signalsLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading signal data...</div>
      </div>
    );
  }

  const signalAction = signals?.signal_action ?? status?.paper_trading?.signal_action ?? "NO_SIGNAL";
  const bestCandidate = signals?.best_candidate;
  const allCandidates = signals?.all_candidates ?? [];
  const blockedCandidates = signals?.blocked_candidates ?? [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Signals & Risk Gates</h1>
          <p className="text-muted-foreground">
            Paper trading signal candidates and risk evaluation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={riskStatus?.status ?? "UNKNOWN"} size="lg" />
          {signals?.evidence_classification && (
            <EvidenceBadge classification={signals.evidence_classification} size="lg" />
          )}
        </div>
      </div>

      {/* Signal Action Banner */}
      <div
        className={cn(
          "rounded-lg border p-6",
          signalAction === "PAPER_APPROVED" && "border-status-ok/30 bg-status-ok/10",
          signalAction === "BLOCKED_BY_RISK" && "border-status-watch/30 bg-status-watch/10",
          signalAction === "NO_SIGNAL" && "border-border bg-muted"
        )}
      >
        <div className="flex items-center gap-4">
          {signalAction === "PAPER_APPROVED" ? (
            <CheckCircle className="h-8 w-8 text-status-ok" />
          ) : signalAction === "BLOCKED_BY_RISK" ? (
            <Ban className="h-8 w-8 text-status-watch" />
          ) : (
            <AlertCircle className="h-8 w-8 text-muted-foreground" />
          )}
          <div>
            <h2 className={cn(
              "text-xl font-bold",
              signalAction === "PAPER_APPROVED" && "text-status-ok",
              signalAction === "BLOCKED_BY_RISK" && "text-status-watch",
              signalAction === "NO_SIGNAL" && "text-foreground"
            )}>
              {signalAction.replace(/_/g, " ")}
            </h2>
            <p className="text-muted-foreground">
              {signalAction === "PAPER_APPROVED" 
                ? "A signal candidate has passed all risk gates"
                : signalAction === "BLOCKED_BY_RISK"
                  ? "All candidates were blocked by risk gates"
                  : signals?.reason ?? "No trading signal generated for this evaluation period"}
            </p>
          </div>
        </div>
      </div>

      {/* Risk Gates Summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Gates Status</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {riskStatus 
                ? `${riskStatus.gates_passed}/${riskStatus.gates_total} PASSED`
                : "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Total Candidates</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {allCandidates.length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Blocked Candidates</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {blockedCandidates.length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Target Date</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {signals?.target_date ?? status?.target_date ?? "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Blocked Reasons */}
      {riskStatus?.blocked_reasons && riskStatus.blocked_reasons.length > 0 && (
        <div className="rounded-lg border border-status-blocked/30 bg-status-blocked/10 p-4">
          <div className="flex items-start gap-3">
            <XCircle className="mt-0.5 h-5 w-5 text-status-blocked" />
            <div>
              <h3 className="font-medium text-status-blocked">Blocked Reasons</h3>
              <ul className="mt-1 space-y-1">
                {riskStatus.blocked_reasons.map((reason, i) => (
                  <li key={i} className="text-sm text-status-blocked/80">
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Best Candidate Details */}
      {bestCandidate && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <CardTitle>Best Candidate</CardTitle>
            </div>
            <CardDescription>
              Top-ranked signal candidate with gate evaluation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Candidate Info */}
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-muted-foreground">Contract</div>
                  <div className="font-mono text-lg font-bold text-foreground">
                    {bestCandidate.contract_ticker}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {bestCandidate.contract_title}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Side</div>
                    <div className={cn(
                      "text-lg font-bold",
                      bestCandidate.side === "YES" ? "text-status-ok" : "text-status-blocked"
                    )}>
                      {bestCandidate.side}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Recommended Size</div>
                    <div className="text-lg font-bold text-foreground">
                      {bestCandidate.recommended_size ?? "N/A"}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Model Prob</div>
                    <div className="font-mono text-foreground">
                      {formatPercentage(bestCandidate.model_probability)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Market Prob</div>
                    <div className="font-mono text-foreground">
                      {formatPercentage(bestCandidate.market_probability)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Edge</div>
                    <div className={cn(
                      "font-mono font-medium",
                      bestCandidate.edge > 0 ? "text-status-ok" : "text-status-blocked"
                    )}>
                      {bestCandidate.edge > 0 ? "+" : ""}{formatPercentage(bestCandidate.edge)}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-muted-foreground">Kelly Fraction</div>
                  <div className="font-mono text-foreground">
                    {formatPercentage(bestCandidate.kelly_fraction, 2)}
                  </div>
                </div>
              </div>

              {/* Gate Results */}
              <div>
                <h4 className="mb-3 text-sm font-medium text-muted-foreground">
                  Risk Gates
                </h4>
                <div className="space-y-2">
                  {bestCandidate.gates?.map((gate, i) => (
                    <GateRow key={i} gate={gate} />
                  ))}
                </div>

                {bestCandidate.rejection_reason && (
                  <div className="mt-4 rounded-lg border border-status-blocked/30 bg-status-blocked/10 p-3">
                    <div className="text-sm font-medium text-status-blocked">
                      Rejection Reason
                    </div>
                    <div className="text-sm text-status-blocked/80">
                      {bestCandidate.rejection_reason}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* All Candidates Table */}
      {allCandidates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>All Signal Candidates</CardTitle>
            <CardDescription>
              Complete list of evaluated signal candidates
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
                      Side
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Model
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Market
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Edge
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                      Kelly
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                      Gate Result
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {allCandidates.map((candidate, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/50 hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 font-mono text-sm text-foreground">
                        {candidate.contract_ticker}
                      </td>
                      <td className={cn(
                        "px-4 py-3 text-sm font-medium",
                        candidate.side === "YES" ? "text-status-ok" : "text-status-blocked"
                      )}>
                        {candidate.side}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {formatPercentage(candidate.model_probability)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {formatPercentage(candidate.market_probability)}
                      </td>
                      <td className={cn(
                        "px-4 py-3 text-right font-mono text-sm",
                        candidate.edge > 0 ? "text-status-ok" : "text-status-blocked"
                      )}>
                        {candidate.edge > 0 ? "+" : ""}{formatPercentage(candidate.edge)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-muted-foreground">
                        {formatPercentage(candidate.kelly_fraction, 2)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={candidate.overall_gate_result}
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

      {/* Blocked Candidates Audit */}
      {blockedCandidates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Blocked Candidates Audit</CardTitle>
            <CardDescription>
              Candidates blocked by risk gates with rejection reasons
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {blockedCandidates.map((candidate, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-border bg-muted/50 p-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-mono font-medium text-foreground">
                        {candidate.contract_ticker}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {candidate.side} | Edge: {formatPercentage(candidate.edge)}
                      </div>
                    </div>
                    <StatusBadge status="FAIL" size="sm" />
                  </div>
                  {candidate.rejection_reason && (
                    <div className="mt-2 text-sm text-status-blocked">
                      {candidate.rejection_reason}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Freshness */}
      <FreshnessCard
        title="Signal Data Freshness"
        description="Time since last signal evaluation"
        timestamp={signals?.timestamp}
      />
    </div>
  );
}

function GateRow({ gate }: { gate: RiskGate }) {
  const Icon = gate.result === "PASS" 
    ? CheckCircle 
    : gate.result === "FAIL" 
      ? XCircle 
      : AlertTriangle;

  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted/50 px-4 py-2">
      <div className="flex items-center gap-3">
        <Icon className={cn(
          "h-4 w-4",
          gate.result === "PASS" && "text-status-ok",
          gate.result === "FAIL" && "text-status-blocked",
          gate.result === "SKIP" && "text-muted-foreground"
        )} />
        <span className="text-sm text-foreground">{gate.gate_name}</span>
      </div>
      <div className="flex items-center gap-2">
        {gate.reason && (
          <span className="text-xs text-muted-foreground">{gate.reason}</span>
        )}
        <StatusBadge status={gate.result} size="sm" showDot={false} />
      </div>
    </div>
  );
}
