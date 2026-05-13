"use client";

import Link from "next/link";
import { 
  Cloud, 
  TrendingUp, 
  BarChart3, 
  AlertCircle,
  BookOpen,
  Target,
  ArrowRight,
  AlertTriangle,
  Thermometer,
} from "lucide-react";
import { useStatus, useWeather, useMarkets, useSignals, useLedger } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { EvidenceBadge } from "@/components/dashboard/evidence-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn, formatCurrency } from "@/lib/utils";

export default function OverviewPage() {
  const { data: statusData, isLoading: statusLoading } = useStatus();
  const { data: weatherData } = useWeather();
  const { data: marketsData } = useMarkets();
  const { data: signalsData } = useSignals();
  const { data: ledgerData } = useLedger();

  const status = statusData?.data;
  const weather = weatherData?.data;
  const markets = marketsData?.data;
  const signals = signalsData?.data;
  const ledger = ledgerData?.data;

  if (statusLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Overview</h1>
          <p className="text-muted-foreground">
            KMIA Temperature Paper Trading Dashboard
          </p>
        </div>
        {status && (
          <div className="flex items-center gap-3">
            <StatusBadge status={status.overall_status} size="lg" />
            <EvidenceBadge classification={status.evidence_classification} size="lg" />
          </div>
        )}
      </div>

      {/* Warning Banner if needed */}
      {status?.warnings && status.warnings.length > 0 && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">Active Warnings</h3>
              <ul className="mt-1 space-y-1">
                {status.warnings.map((warning, i) => (
                  <li key={i} className="text-sm text-status-watch/80">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Key Metrics Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Temperature Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Current Temperature
            </CardTitle>
            <Thermometer className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-foreground">
              {weather?.temperature_f != null ? `${weather.temperature_f}°F` : "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">
              {status?.weather?.source ?? "KMIA Station"}
            </p>
          </CardContent>
        </Card>

        {/* Active Contracts Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Contracts
            </CardTitle>
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-foreground">
              {status?.market?.active_contracts ?? markets?.contracts?.length ?? "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">
              {status?.market?.series_ticker ?? "Loading..."}
            </p>
          </CardContent>
        </Card>

        {/* Paper Balance Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Paper Balance
            </CardTitle>
            <BookOpen className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-foreground">
              {ledger?.balance_cents != null 
                ? formatCurrency(ledger.balance_cents)
                : "N/A"}
            </div>
            <p className={cn(
              "text-xs",
              ledger?.total_pnl_cents && ledger.total_pnl_cents > 0 
                ? "text-status-ok" 
                : ledger?.total_pnl_cents && ledger.total_pnl_cents < 0 
                  ? "text-status-blocked" 
                  : "text-muted-foreground"
            )}>
              {ledger?.total_pnl_cents != null 
                ? `${ledger.total_pnl_cents >= 0 ? "+" : ""}${formatCurrency(ledger.total_pnl_cents)} PnL`
                : "No positions"}
            </p>
          </CardContent>
        </Card>

        {/* Signal Status Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Signal Status
            </CardTitle>
            <AlertCircle className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-foreground">
              {signals?.signal_action 
                ? signals.signal_action.replace(/_/g, " ")
                : status?.paper_trading?.signal_action?.replace(/_/g, " ") 
                ?? "NO SIGNAL"}
            </div>
            <p className="text-xs text-muted-foreground">
              {status?.risk_gates 
                ? `${status.risk_gates.gates_passed}/${status.risk_gates.gates_total} gates passed`
                : "Loading..."}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Data Freshness Grid */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-foreground">Data Freshness</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FreshnessCard
            title="Weather Data"
            description="NWS KMIA observations"
            timestamp={status?.weather?.last_update ?? weather?.timestamp}
          >
            <StatusBadge status={status?.weather?.status ?? "UNKNOWN"} size="sm" />
          </FreshnessCard>

          <FreshnessCard
            title="Market Data"
            description="Kalshi contract snapshots"
            timestamp={markets?.timestamp}
          >
            <StatusBadge status={status?.market?.status ?? "UNKNOWN"} size="sm" />
          </FreshnessCard>

          <FreshnessCard
            title="Orderbooks"
            description="Bid/ask depth data"
            timestamp={status?.market?.orderbook_freshness}
          >
            <span className="text-sm text-muted-foreground">
              {status?.market?.active_contracts ?? 0} contracts tracked
            </span>
          </FreshnessCard>

          <FreshnessCard
            title="Forecast Model"
            description="Temperature distribution"
            timestamp={status?.timestamp}
          >
            <StatusBadge status={status?.forecast?.status ?? "UNKNOWN"} size="sm" />
          </FreshnessCard>

          <FreshnessCard
            title="Paper Signal"
            description="Latest trading signal"
            timestamp={signals?.timestamp}
          >
            <StatusBadge 
              status={signals?.signal_action === "PAPER_APPROVED" ? "OK" : "WATCH"} 
              size="sm" 
            />
          </FreshnessCard>

          <FreshnessCard
            title="Risk Gates"
            description="Gate evaluation status"
            timestamp={status?.timestamp}
          >
            <StatusBadge status={status?.risk_gates?.status ?? "UNKNOWN"} size="sm" />
          </FreshnessCard>
        </div>
      </div>

      {/* Quick Links */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-foreground">Quick Links</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <QuickLinkCard
            href="/weather"
            icon={Cloud}
            title="Weather Data"
            description="View KMIA temperature observations and forecasts"
          />
          <QuickLinkCard
            href="/markets"
            icon={TrendingUp}
            title="Kalshi Markets"
            description="Browse active contracts and orderbooks"
          />
          <QuickLinkCard
            href="/forecast"
            icon={BarChart3}
            title="Forecast Distribution"
            description="View integer temperature probabilities"
          />
          <QuickLinkCard
            href="/signals"
            icon={AlertCircle}
            title="Signals & Risk"
            description="Review signal candidates and risk gates"
          />
          <QuickLinkCard
            href="/ledger"
            icon={BookOpen}
            title="Paper Ledger"
            description="Track paper positions and PnL"
          />
          <QuickLinkCard
            href="/calibration"
            icon={Target}
            title="Calibration"
            description="View model accuracy and backtests"
          />
        </div>
      </div>
    </div>
  );
}

function QuickLinkCard({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: typeof Cloud;
  title: string;
  description: string;
}) {
  return (
    <Link href={href}>
      <Card className="group transition-colors hover:bg-accent">
        <CardContent className="flex items-center gap-4 p-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-foreground group-hover:text-accent-foreground">
              {title}
            </h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
        </CardContent>
      </Card>
    </Link>
  );
}
