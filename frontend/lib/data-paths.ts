import path from "path";

// Base path to the backend data directory
// In production, this would be configured via environment variable
const BACKEND_DATA_PATH = process.env.BACKEND_DATA_PATH || path.join(process.cwd(), "..", "backend", "data", "processed");

export const DATA_PATHS = {
  // Daily status
  statusDir: path.join(BACKEND_DATA_PATH, "status"),
  statusPattern: "kmia_daily_status_*.json",
  
  // Weather data
  weatherLatest: path.join(BACKEND_DATA_PATH, "weather_nws", "latest_nws_kmia_snapshot.json"),
  
  // Kalshi market data
  marketLatest: path.join(BACKEND_DATA_PATH, "kalshi_market_snapshots", "latest_kalshi_market_snapshot.json"),
  orderbooksLatest: path.join(BACKEND_DATA_PATH, "kalshi_market_snapshots", "latest_kalshi_orderbooks.json"),
  
  // Paper trading
  paperSignalLatest: path.join(BACKEND_DATA_PATH, "paper_trading", "latest_paper_signal.json"),
  paperLedger: path.join(BACKEND_DATA_PATH, "paper_trading", "paper_trade_ledger.jsonl"),
  
  // Forecast
  forecastDir: path.join(BACKEND_DATA_PATH, "forecasts"),
  forecastPattern: "kmia_forecast_*.json",
  
  // Calibration
  calibration: path.join(BACKEND_DATA_PATH, "aggregate_calibration", "aggregate_calibration.json"),
  
  // Reports
  reportsDir: path.join(BACKEND_DATA_PATH, "reports"),
  
  // Logs
  logsDir: path.join(BACKEND_DATA_PATH, "logs"),
} as const;

export function getLatestFileInDir(dir: string, pattern: string): string | null {
  // This will be implemented in API routes using fs
  return null;
}
