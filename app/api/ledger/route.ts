import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const BACKEND_DATA_PATH = process.env.BACKEND_DATA_PATH || path.join(process.cwd(), "..", "backend", "data", "processed");

export async function GET() {
  try {
    const ledgerFile = path.join(BACKEND_DATA_PATH, "paper_trading", "paper_trade_ledger.jsonl");
    
    try {
      await fs.access(ledgerFile);
    } catch {
      // Return empty ledger if file doesn't exist yet
      return NextResponse.json({
        data: {
          balance_cents: 10000000, // $100,000 default
          initial_balance_cents: 10000000,
          entries: [],
          open_positions: [],
          settled_positions: [],
          total_pnl_cents: 0,
        },
        error: null,
        missing: false,
        timestamp: new Date().toISOString(),
      });
    }

    const content = await fs.readFile(ledgerFile, "utf-8");
    const lines = content.trim().split("\n").filter(Boolean);
    const entries = lines.map((line) => JSON.parse(line));

    // Calculate positions and balance
    const initialBalance = 10000000; // $100,000
    let balance = initialBalance;
    const openPositions: typeof entries = [];
    const settledPositions: typeof entries = [];
    let totalPnl = 0;

    for (const entry of entries) {
      if (entry.entry_type === "OPEN") {
        openPositions.push(entry);
        balance -= entry.price_cents * entry.quantity;
      } else if (entry.entry_type === "SETTLE" || entry.entry_type === "EXPIRE") {
        settledPositions.push(entry);
        if (entry.pnl_cents) {
          balance += entry.pnl_cents;
          totalPnl += entry.pnl_cents;
        }
        // Remove from open positions
        const idx = openPositions.findIndex(
          (p) => p.contract_ticker === entry.contract_ticker && p.side === entry.side
        );
        if (idx !== -1) openPositions.splice(idx, 1);
      }
    }

    return NextResponse.json({
      data: {
        balance_cents: balance,
        initial_balance_cents: initialBalance,
        entries,
        open_positions: openPositions,
        settled_positions: settledPositions,
        total_pnl_cents: totalPnl,
      },
      error: null,
      missing: false,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json({
      data: null,
      error: error instanceof Error ? error.message : "Unknown error",
      missing: true,
      timestamp: new Date().toISOString(),
    });
  }
}
