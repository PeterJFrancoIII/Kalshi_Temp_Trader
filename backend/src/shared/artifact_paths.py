"""
Centralized registry for critical runtime artifact paths.
Phase 1 of V2 Hyper Refactor Plan.
"""

from pathlib import Path

# Base directory for this file is backend/src/shared
# So parents[2] is backend
BACKEND_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DATA_DIR = BACKEND_ROOT / "data" / "processed"
WEATHER_NWS_DIR = PROCESSED_DATA_DIR / "weather_nws"
KALSHI_MARKET_SNAPSHOT_DIR = PROCESSED_DATA_DIR / "kalshi_market_snapshots"
PAPER_TRADING_DIR = PROCESSED_DATA_DIR / "paper_trading"
STATUS_DIR = PROCESSED_DATA_DIR / "status"
REPORTS_DIR = PROCESSED_DATA_DIR / "reports"

LATEST_NWS_KMIA_SNAPSHOT = WEATHER_NWS_DIR / "latest_nws_kmia_snapshot.json"
LATEST_KALSHI_MARKET_SNAPSHOT = KALSHI_MARKET_SNAPSHOT_DIR / "latest_kalshi_market_snapshot.json"
LATEST_KALSHI_ORDERBOOKS = KALSHI_MARKET_SNAPSHOT_DIR / "latest_kalshi_orderbooks.json"
LATEST_PAPER_SIGNAL = PAPER_TRADING_DIR / "latest_paper_signal.json"

LATEST_KMIA_DAILY_STATUS_JSON = STATUS_DIR / "latest_kmia_daily_status.json"
LATEST_KMIA_DAILY_STATUS_MD = STATUS_DIR / "latest_kmia_daily_status.md"
