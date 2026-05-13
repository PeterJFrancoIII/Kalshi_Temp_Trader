"use client";

import { useState } from "react";
import { TrendingUp, AlertTriangle, Search, ArrowUpDown } from "lucide-react";
import { useMarkets, useOrderbooks, useStatus } from "@/hooks/use-data";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { FreshnessCard } from "@/components/dashboard/freshness-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { cn, formatTimestamp, formatCurrency } from "@/lib/utils";

type SortField = "ticker" | "yes_bid" | "yes_ask" | "last_price" | "volume";
type SortDir = "asc" | "desc";

export default function MarketsPage() {
  const { data: marketsData, isLoading: marketsLoading } = useMarkets();
  const { data: orderbooksData } = useOrderbooks();
  const { data: statusData } = useStatus();

  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("ticker");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const markets = marketsData?.data;
  const orderbooks = orderbooksData?.data;
  const status = statusData?.data;
  const marketStatus = status?.market;

  const contracts = markets?.contracts ?? [];

  // Filter and sort contracts
  const filteredContracts = contracts
    .filter((c) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        c.ticker.toLowerCase().includes(query) ||
        c.title.toLowerCase().includes(query) ||
        (c.subtitle?.toLowerCase().includes(query) ?? false)
      );
    })
    .sort((a, b) => {
      let aVal: number | string = 0;
      let bVal: number | string = 0;

      switch (sortField) {
        case "ticker":
          aVal = a.ticker;
          bVal = b.ticker;
          break;
        case "yes_bid":
          aVal = a.yes_bid ?? -1;
          bVal = b.yes_bid ?? -1;
          break;
        case "yes_ask":
          aVal = a.yes_ask ?? -1;
          bVal = b.yes_ask ?? -1;
          break;
        case "last_price":
          aVal = a.last_price ?? -1;
          bVal = b.last_price ?? -1;
          break;
        case "volume":
          aVal = a.volume ?? 0;
          bVal = b.volume ?? 0;
          break;
      }

      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDir === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  if (marketsLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading market data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Kalshi Markets</h1>
          <p className="text-muted-foreground">
            {markets?.series_ticker ?? "KMIA Temperature Contracts"}
          </p>
        </div>
        <StatusBadge status={marketStatus?.status ?? "UNKNOWN"} size="lg" />
      </div>

      {/* Errors/Warnings */}
      {marketStatus?.errors && marketStatus.errors.length > 0 && (
        <div className="rounded-lg border border-status-blocked/30 bg-status-blocked/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-blocked" />
            <div>
              <h3 className="font-medium text-status-blocked">Market Errors</h3>
              <ul className="mt-1 space-y-1">
                {marketStatus.errors.map((error, i) => (
                  <li key={i} className="text-sm text-status-blocked/80">
                    {error}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Missing Data Warning */}
      {marketsData?.missing && (
        <div className="rounded-lg border border-status-watch/30 bg-status-watch/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-status-watch" />
            <div>
              <h3 className="font-medium text-status-watch">Data Unavailable</h3>
              <p className="text-sm text-status-watch/80">
                {marketsData.error || "Market data file not found. The backend may not have run yet."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Market Summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Event Ticker</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {markets?.event_ticker ?? marketStatus?.event_ticker ?? "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Series Ticker</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {markets?.series_ticker ?? marketStatus?.series_ticker ?? "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Active Contracts</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {contracts.length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Last Update</div>
            <div className="mt-1 text-lg font-bold text-foreground">
              {formatTimestamp(markets?.timestamp)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Freshness */}
      <div className="grid gap-4 sm:grid-cols-2">
        <FreshnessCard
          title="Market Snapshot"
          description="Contract prices and volumes"
          timestamp={markets?.timestamp}
        />
        <FreshnessCard
          title="Orderbook Data"
          description="Bid/ask depth"
          timestamp={orderbooks?.timestamp ?? marketStatus?.orderbook_freshness}
        />
      </div>

      {/* Contracts Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Active Contracts</CardTitle>
              <CardDescription>
                {filteredContracts.length} of {contracts.length} contracts shown
              </CardDescription>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search contracts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-9 w-64 rounded-md border border-input bg-background pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <SortableHeader
                    label="Ticker"
                    field="ticker"
                    currentField={sortField}
                    currentDir={sortDir}
                    onSort={handleSort}
                  />
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    Range
                  </th>
                  <SortableHeader
                    label="Bid"
                    field="yes_bid"
                    currentField={sortField}
                    currentDir={sortDir}
                    onSort={handleSort}
                    align="right"
                  />
                  <SortableHeader
                    label="Ask"
                    field="yes_ask"
                    currentField={sortField}
                    currentDir={sortDir}
                    onSort={handleSort}
                    align="right"
                  />
                  <SortableHeader
                    label="Last"
                    field="last_price"
                    currentField={sortField}
                    currentDir={sortDir}
                    onSort={handleSort}
                    align="right"
                  />
                  <SortableHeader
                    label="Volume"
                    field="volume"
                    currentField={sortField}
                    currentDir={sortDir}
                    onSort={handleSort}
                    align="right"
                  />
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredContracts.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                      {contracts.length === 0 
                        ? "No contracts available" 
                        : "No contracts match your search"}
                    </td>
                  </tr>
                ) : (
                  filteredContracts.map((contract) => (
                    <tr
                      key={contract.ticker}
                      className="border-b border-border/50 hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 font-mono text-sm text-foreground">
                        {contract.ticker}
                      </td>
                      <td className="px-4 py-3 text-sm text-foreground">
                        {contract.title}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {contract.floor_strike != null && contract.cap_strike != null
                          ? `${contract.floor_strike}°F - ${contract.cap_strike}°F`
                          : contract.subtitle ?? "N/A"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {contract.yes_bid != null ? formatCurrency(contract.yes_bid) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {contract.yes_ask != null ? formatCurrency(contract.yes_ask) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-foreground">
                        {contract.last_price != null ? formatCurrency(contract.last_price) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-sm text-muted-foreground">
                        {contract.volume?.toLocaleString() ?? "0"}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={contract.status === "active" ? "OK" : "BLOCKED"}
                          size="sm"
                          showDot={false}
                        />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SortableHeader({
  label,
  field,
  currentField,
  currentDir,
  onSort,
  align = "left",
}: {
  label: string;
  field: SortField;
  currentField: SortField;
  currentDir: SortDir;
  onSort: (field: SortField) => void;
  align?: "left" | "right";
}) {
  const isActive = currentField === field;

  return (
    <th
      className={cn(
        "cursor-pointer px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground",
        align === "right" && "text-right"
      )}
      onClick={() => onSort(field)}
    >
      <div className={cn("flex items-center gap-1", align === "right" && "justify-end")}>
        {label}
        <ArrowUpDown
          className={cn(
            "h-4 w-4",
            isActive ? "text-primary" : "text-muted-foreground/50"
          )}
        />
      </div>
    </th>
  );
}
