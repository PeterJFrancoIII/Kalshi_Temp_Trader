// Evidence classification
export type EvidenceClassification = "VALID_PAPER_EVAL" | "SAFETY_ONLY" | "INVALID";

// Overall status
export type OverallStatus = "OK" | "WATCH" | "BLOCKED" | "INVALID";

// Gate result
export type GateResult = "PASS" | "FAIL" | "SKIP" | "UNKNOWN";

// Daily status from backend
export interface DailyStatus {
  timestamp: string;
  target_date: string;
  overall_status: OverallStatus;
  evidence_classification: EvidenceClassification;
  weather: {
    status: string;
    last_update: string | null;
    temperature_f: number | null;
    source: string;
    errors: string[];
  };
  market: {
    status: string;
    event_ticker: string | null;
    series_ticker: string | null;
    active_contracts: number;
    orderbook_freshness: string | null;
    errors: string[];
  };
  forecast: {
    status: string;
    model_type: string | null;
    distribution_sum: number | null;
    mapping_warnings: string[];
    errors: string[];
  };
  risk_gates: {
    status: string;
    gates_passed: number;
    gates_total: number;
    blocked_reasons: string[];
  };
  paper_trading: {
    status: string;
    signal_generated: boolean;
    signal_action: string | null;
    paper_balance_cents: number | null;
    errors: string[];
  };
  warnings: string[];
  errors: string[];
}

// Weather data
export interface WeatherData {
  timestamp: string;
  station_id: string;
  temperature_f: number | null;
  temperature_c: number | null;
  humidity_percent: number | null;
  wind_speed_mph: number | null;
  wind_direction: string | null;
  conditions: string | null;
  raw_observation: Record<string, unknown>;
}

// Kalshi contract
export interface KalshiContract {
  ticker: string;
  title: string;
  subtitle: string | null;
  floor_strike: number | null;
  cap_strike: number | null;
  yes_bid: number | null;
  yes_ask: number | null;
  last_price: number | null;
  volume: number;
  open_interest: number;
  status: string;
}

// Market snapshot
export interface MarketSnapshot {
  timestamp: string;
  event_ticker: string;
  series_ticker: string;
  contracts: KalshiContract[];
  errors: string[];
}

// Orderbook entry
export interface OrderbookEntry {
  price: number;
  quantity: number;
}

// Orderbook
export interface Orderbook {
  ticker: string;
  yes_bids: OrderbookEntry[];
  yes_asks: OrderbookEntry[];
  no_bids: OrderbookEntry[];
  no_asks: OrderbookEntry[];
}

// Orderbooks snapshot
export interface OrderbooksSnapshot {
  timestamp: string;
  orderbooks: Record<string, Orderbook>;
}

// Forecast distribution
export interface ForecastDistribution {
  timestamp: string;
  model_type: string;
  target_date: string;
  probabilities: Record<string, number>;
  cumulative: Record<string, number>;
  metadata: Record<string, unknown>;
}

// Risk gate
export interface RiskGate {
  gate_name: string;
  result: GateResult;
  reason: string | null;
  details: Record<string, unknown>;
}

// Signal candidate
export interface SignalCandidate {
  contract_ticker: string;
  contract_title: string;
  side: "YES" | "NO";
  model_probability: number;
  market_probability: number;
  edge: number;
  kelly_fraction: number;
  recommended_size: number;
  gates: RiskGate[];
  overall_gate_result: GateResult;
  rejection_reason: string | null;
}

// Paper signal
export interface PaperSignal {
  timestamp: string;
  target_date: string;
  signal_action: "NO_SIGNAL" | "BLOCKED_BY_RISK" | "PAPER_APPROVED";
  evidence_classification: EvidenceClassification;
  best_candidate: SignalCandidate | null;
  all_candidates: SignalCandidate[];
  blocked_candidates: SignalCandidate[];
  reason: string | null;
}

// Ledger entry
export interface LedgerEntry {
  timestamp: string;
  entry_type: "OPEN" | "SETTLE" | "EXPIRE" | "BLOCKED";
  contract_ticker: string;
  side: "YES" | "NO";
  quantity: number;
  price_cents: number;
  settlement_price_cents: number | null;
  pnl_cents: number | null;
  reason: string | null;
}

// Paper ledger
export interface PaperLedger {
  balance_cents: number;
  initial_balance_cents: number;
  entries: LedgerEntry[];
  open_positions: LedgerEntry[];
  settled_positions: LedgerEntry[];
  total_pnl_cents: number;
}

// Calibration data
export interface CalibrationData {
  timestamp: string;
  total_settlements: number;
  correct_settlements: number;
  accuracy: number;
  excluded_days: string[];
  by_bucket: Record<string, { count: number; correct: number; accuracy: number }>;
}

// API response wrapper
export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  missing: boolean;
  timestamp: string;
}
