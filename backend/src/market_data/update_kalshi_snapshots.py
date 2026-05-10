import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
from market_data.kalshi_public_client import KalshiPublicClient

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def normalize_orderbook(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Kalshi orderbook response."""
    warnings = []
    orderbook_data = raw.get("orderbook", raw)
    
    yes_bids = orderbook_data.get("yes", [])
    no_bids = orderbook_data.get("no", [])
    
    # Ensure they are lists
    if not isinstance(yes_bids, list):
        warnings.append("yes_bids is not a list")
        yes_bids = []
    if not isinstance(no_bids, list):
        warnings.append("no_bids is not a list")
        no_bids = []
        
    return {
        "yes_bids": yes_bids,
        "no_bids": no_bids,
        "warnings": warnings
    }

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
        # 1. Manual Market Ticker Lookup
        manual_matches = []
        missing_known_tickers = []
        if known_markets:
            print(f"Checking {len(known_markets)} known market tickers...")
            for ticker in known_markets:
                try:
                    m_resp = client.get_market(ticker)
                    m = m_resp.get("market")
                    if m:
                        manual_matches.append(m)
                        print(f"  Found known market: {ticker}")
                    else:
                        missing_known_tickers.append(ticker)
                except Exception as e:
                    print(f"  Warning: Could not fetch known market {ticker}: {e}")
                    missing_known_tickers.append(ticker)

        # 2. Manual Series Lookup
        missing_known_series = []
        if known_series:
            print(f"Checking {len(known_series)} known series tickers...")
            for series in known_series:
                try:
                    s_resp = client.get_markets_for_series(series)
                    s_markets = s_resp.get("markets", [])
                    if s_markets:
                        manual_matches.extend(s_markets)
                        print(f"  Found {len(s_markets)} markets for series: {series}")
                    else:
                        missing_known_series.append(series)
                except Exception as e:
                    print(f"  Warning: Could not fetch series {series}: {e}")
                    missing_known_series.append(series)

        # 3. Auto-Discovery Fallback
        discovery_result = client.discover_temperature_markets(search_terms)
        candidates = discovery_result.get("candidate_markets", [])
        attempts = discovery_result.get("endpoint_attempts", [])
        raw_count = discovery_result.get("total_raw_markets_seen", 0)
        
        print(f"Auto-discovery complete. Raw markets seen: {raw_count}")
        
        # 4. Refined Auto-Selection
        auto_selected = []
        for m in candidates:
            m_ticker = m.get("ticker", "").upper()
            m_series = m.get("series_ticker", "").upper()
            title = m.get("title", "")
            subtitle = m.get("subtitle", "")
            text = (f"{title} {subtitle} {m_ticker} {m_series}").lower()
            
            # Score based on preferred terms
            if all(pt.lower() in text for pt in preferred_terms):
                auto_selected.append(m)
        
        # Combine (deduplicate by ticker)
        all_selected_map = {m.get("ticker"): m for m in auto_selected}
        for m in manual_matches:
            all_selected_map[m.get("ticker")] = m
            
        final_selected = list(all_selected_map.values())
        
        # Fetch Orderbooks for selected markets
        orderbooks = {}
        orderbook_status = "OK"
        orderbook_warnings = []
        
        if not final_selected:
            orderbook_status = "EMPTY"
            orderbook_warnings.append("No active KXHIGHMIA markets available for orderbook fetch")
        else:
            print(f"Fetching orderbooks for {len(final_selected)} markets...")
            for m in final_selected:
                ticker = m.get("ticker")
                try:
                    raw_ob = client.get_orderbook(ticker)
                    normalized_ob = normalize_orderbook(raw_ob)
                    orderbooks[ticker] = normalized_ob
                except Exception as e:
                    print(f"  Warning: Could not fetch orderbook for {ticker}: {e}")
                    orderbooks[ticker] = {
                        "yes_bids": [],
                        "no_bids": [],
                        "warnings": [str(e)]
                    }
                    orderbook_warnings.append(f"Failed to fetch orderbook for {ticker}")
                    
        # Write Orderbook Artifact
        orderbook_artifact = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "kalshi",
            "status": orderbook_status,
            "warnings": orderbook_warnings,
            "orderbooks": orderbooks
        }
        
        ob_filepath = OUTPUT_DIR / "latest_kalshi_orderbooks.json"
        try:
            with open(ob_filepath, 'w') as f:
                json.dump(orderbook_artifact, f, indent=2)
            print(f"Orderbooks saved to: {ob_filepath}")
        except Exception as e:
            print(f"Error writing orderbooks artifact: {e}")
        
        print(f"Candidate markets: {len(candidates)}")
        print(f"Selected markets: {len(final_selected)} ({len(auto_selected)} auto, {len(manual_matches)} manual)")
        
        next_action = "None. System is healthy."
        warnings = []
        if not final_selected:
            warnings.append("No matching Miami/KMIA temperature market found.")
            next_action = "Auto-discovery found no Miami/KMIA temperature market. Add a known ticker or series to backend/config/kalshi_market_discovery.json."
        
        if missing_known_tickers:
            warnings.append(f"Missing known market tickers: {missing_known_tickers}")
        if missing_known_series:
            warnings.append(f"Missing known series tickers: {missing_known_series}")
            
        if final_selected and (known_markets or known_series):
            next_action = "Known ticker tracking is active."

        snapshot = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "read_only_public_market_data",
            "base_url": client.base_url,
            "search_terms_used": search_terms,
            "known_market_tickers_used": known_markets,
            "known_series_tickers_used": known_series,
            "manual_matches": manual_matches,
            "missing_known_tickers": missing_known_tickers,
            "missing_known_series": missing_known_series,
            "endpoint_attempts": attempts,
            "total_raw_markets_seen": raw_count,
            "candidate_markets_count": len(candidates),
            "selected_temperature_markets": final_selected,
            "markets_found": len(final_selected),
            "markets": final_selected,
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
        print(f"\nSnapshot saved to: {saved_path}")
        print("Success.")
        
    except Exception as e:
        print(f"Error updating Kalshi snapshots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
