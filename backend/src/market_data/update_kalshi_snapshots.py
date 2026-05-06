import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from market_data.kalshi_public_client import KalshiPublicClient

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def main():
    print("--- Kalshi Public Market Data Updater ---")
    print("Mode: READ-ONLY / PAPER EVALUATION")
    
    # ROOT resolution
    ROOT = Path(__file__).resolve().parents[3]
    CONFIG_PATH = ROOT / "backend" / "config" / "kalshi_market_discovery.json"
    OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "kalshi_market_snapshots"
    
    # Load Config
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "search_terms": ["Miami", "KMIA", "temperature", "high"],
            "preferred_terms": ["Miami", "temperature", "high"],
            "known_series_tickers": [],
            "known_market_tickers": []
        }

    search_terms = config.get("search_terms", [])
    preferred_terms = config.get("preferred_terms", [])
    known_series = config.get("known_series_tickers", [])
    known_markets = config.get("known_market_tickers", [])
    
    client = KalshiPublicClient()
    print(f"Discovering markets using terms: {search_terms}...")
    
    try:
        # Discovery Result
        discovery_result = client.discover_temperature_markets(search_terms)
        candidates = discovery_result.get("candidate_markets", [])
        attempts = discovery_result.get("endpoint_attempts", [])
        raw_count = discovery_result.get("total_raw_markets_seen", 0)
        
        # Selection Logic
        selected = []
        for m in candidates:
            ticker = m.get("ticker", "").upper()
            series = m.get("series_ticker", "").upper()
            text = (f"{m.get('title', '')} {m.get('subtitle', '')} {ticker} {series}").lower()
            
            # 1. Check known tickers first
            if ticker in [t.upper() for t in known_markets] or series in [s.upper() for s in known_series]:
                selected.append(m)
                continue
                
            # 2. Score based on preferred terms
            if all(pt.lower() in text for pt in preferred_terms):
                selected.append(m)
        
        print(f"Total raw markets seen: {raw_count}")
        print(f"Candidate markets: {len(candidates)}")
        print(f"Selected Miami temperature markets: {len(selected)}")
        
        next_action = "None. System is healthy."
        warnings = []
        if not selected:
            warnings.append("No matching Miami/KMIA temperature market found.")
            next_action = "Review Kalshi market naming manually or add a known series/ticker to backend/config/kalshi_market_discovery.json."

        snapshot = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "read_only_public_market_data",
            "base_url": client.base_url,
            "search_terms_used": search_terms,
            "endpoint_attempts": attempts,
            "total_raw_markets_seen": raw_count,
            "candidate_markets": candidates,
            "selected_temperature_markets": selected,
            "markets_found": len(selected), # Compatibility
            "markets": selected,           # Compatibility
            "warnings": warnings,
            "next_action": next_action,
            "safety": {
                "no_real_trading": True,
                "no_order_execution": True,
                "no_authentication": True,
                "disclaimer": "NO REAL TRADING EXECUTION - DRY-RUN ONLY"
            }
        }
        
        saved_path = client.save_market_snapshot(snapshot, OUTPUT_DIR)
        print(f"Snapshot saved to: {saved_path}")
        print("Success.")
        
    except Exception as e:
        print(f"Error updating Kalshi snapshots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
