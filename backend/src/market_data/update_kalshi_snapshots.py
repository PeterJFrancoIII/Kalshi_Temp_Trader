import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
from market_data.kalshi_public_client import KalshiPublicClient
from shared.artifact_paths import LATEST_KALSHI_ORDERBOOKS
from shared.timestamp_utils import parse_ticker_date

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

# Paths and Config
ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "backend" / "config" / "kalshi_market_discovery.json"
OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "kalshi_market_snapshots"


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

def get_top_of_book(normalized_ob: Dict[str, Any]) -> Dict[str, Any]:
    """Extract top-of-book prices (in dollars) from normalized orderbook."""
    res = {
        "yes_bid": None,
        "yes_ask": None,
        "no_bid": None,
        "no_ask": None
    }
    
    y_bids = normalized_ob.get("yes_bids", [])
    n_bids = normalized_ob.get("no_bids", [])
    
    if y_bids:
        res["yes_bid"] = y_bids[0][0] / 100.0
        # NO ask is 100 - YES bid
        res["no_ask"] = (100 - y_bids[0][0]) / 100.0
        
    if n_bids:
        res["no_bid"] = n_bids[0][0] / 100.0
        # YES ask is 100 - NO bid
        res["yes_ask"] = (100 - n_bids[0][0]) / 100.0
        
    return res

def main():
    print("--- Kalshi Public Market Data Updater ---")
    print("Mode: READ-ONLY / PAPER EVALUATION")
    
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
            
            # Relaxed condition: require "miami" and ("temperature" or "temp") and "high"
            if "miami" in text and ("temperature" in text or "temp" in text) and "high" in text:
                auto_selected.append(m)
        
        # Combine (deduplicate by ticker)
        all_selected_map = {m.get("ticker"): m for m in auto_selected}
        for m in manual_matches:
            all_selected_map[m.get("ticker")] = m
            
        final_selected = list(all_selected_map.values())
        
        # Empty snapshot protection
        preserved_snapshot = False
        latest_path = OUTPUT_DIR / "latest_kalshi_market_snapshot.json"
        
        if not final_selected:
            print("Warning: No active markets found in current fetch.")
            if latest_path.exists():
                try:
                    with open(latest_path, 'r') as f:
                        prev_snapshot = json.load(f)
                    prev_markets = prev_snapshot.get("selected_temperature_markets", [])
                    
                    # Filter for non-expired markets using ET-aware classify_market_date_eligibility
                    from market_data.kalshi_contract_mapper import classify_market_date_eligibility
                    try:
                        from zoneinfo import ZoneInfo
                    except ImportError:
                        from dateutil.tz import gettz as ZoneInfo
                    
                    now_et = datetime.now(ZoneInfo("America/New_York"))
                    fresh_prev_markets = []
                    for m in prev_markets:
                        t_date = parse_ticker_date(m.get("ticker", ""))
                        if t_date:
                            elig = classify_market_date_eligibility(t_date, now_et)
                            # Keep markets that are eligible for today, tomorrow, or not yet open tomorrow
                            if elig["eligible"] or elig["status"] == "NOT_YET_OPEN":
                                fresh_prev_markets.append(m)
                    
                    if fresh_prev_markets:
                        print(f"Preserving {len(fresh_prev_markets)} fresh markets from previous valid snapshot.")
                        final_selected = fresh_prev_markets
                        preserved_snapshot = True
                    else:
                        print("Previous snapshot contains only expired markets. Rejection preserved.")
                except Exception as e:
                    print(f"Error reading previous snapshot: {e}")
        
        # Fetch Orderbooks for selected markets
        orderbooks = {}
        orderbook_status = "OK"
        orderbook_warnings = []
        
        if not final_selected:
            orderbook_status = "EMPTY"
            orderbook_warnings.append("No active markets available for orderbook fetch")
        else:
            if preserved_snapshot:
                orderbook_warnings.append("Orderbooks are based on preserved previous market snapshot.")
                print("Fetching orderbooks for preserved markets...")
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
                
                # MERGE: Update the market object with fresh orderbook prices if available
                ob = orderbooks[ticker]
                tob = get_top_of_book(ob)
                if tob["yes_bid"] is not None:
                    m["yes_bid_dollars"] = tob["yes_bid"]
                if tob["yes_ask"] is not None:
                    m["yes_ask_dollars"] = tob["yes_ask"]
                if tob["no_bid"] is not None:
                    m["no_bid_dollars"] = tob["no_bid"]
                if tob["no_ask"] is not None:
                    m["no_ask_dollars"] = tob["no_ask"]
                    
                # Fallback logic if orderbook depth is empty
                ob = orderbooks[ticker]
                if not ob.get("yes_bids") and not ob.get("no_bids"):
                    # Use fallback from market snapshot if available
                    has_fallback = False
                    fallback_fields = ["yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars"]
                    for field in fallback_fields:
                        if m.get(field) is not None:
                            has_fallback = True
                            break
                            
                    if has_fallback:
                        ob["top_yes_bid_dollars"] = float(m.get("yes_bid_dollars")) if m.get("yes_bid_dollars") else None
                        ob["top_yes_ask_dollars"] = float(m.get("yes_ask_dollars")) if m.get("yes_ask_dollars") else None
                        ob["top_no_bid_dollars"] = float(m.get("no_bid_dollars")) if m.get("no_bid_dollars") else None
                        ob["top_no_ask_dollars"] = float(m.get("no_ask_dollars")) if m.get("no_ask_dollars") else None
                        ob["last_price_dollars"] = float(m.get("last_price_dollars")) if m.get("last_price_dollars") else None
                        
                        ob["yes_bid_size"] = int(float(m.get("yes_bid_size_fp"))) if m.get("yes_bid_size_fp") else None
                        ob["yes_ask_size"] = int(float(m.get("yes_ask_size_fp"))) if m.get("yes_ask_size_fp") else None
                        ob["no_bid_size"] = int(float(m.get("no_bid_size_fp"))) if m.get("no_bid_size_fp") else None
                        ob["no_ask_size"] = int(float(m.get("no_ask_size_fp"))) if m.get("no_ask_size_fp") else None
                        
                        ob["top_of_book_source"] = "market_snapshot_fallback"
                        ob["price_units"] = "dollars"
                        ob["warnings"].append("Orderbook depth unavailable; using market snapshot top-of-book prices.")
                    
        # Write Orderbook Artifact
        orderbook_artifact = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "kalshi",
            "status": orderbook_status,
            "warnings": orderbook_warnings,
            "orderbooks": orderbooks
        }
        
        ob_filepath = LATEST_KALSHI_ORDERBOOKS
        try:
            with open(ob_filepath, 'w') as f:
                f.write(json.dumps(orderbook_artifact, indent=2))
            print(f"Orderbooks saved to: {ob_filepath}")
        except Exception as e:
            print(f"Error writing orderbooks artifact: {e}")
        
        print(f"Candidate markets: {len(candidates)}")
        print(f"Selected markets: {len(final_selected)} ({len(auto_selected)} auto, {len(manual_matches)} manual)")
        
        next_action = "None. System is healthy."
        warnings = []
        
        if not final_selected:
            warnings.append("No currently active Miami high-temperature markets were discovered from Kalshi.")
            next_action = "Auto-discovery found no Miami/KMIA temperature market. Add a known ticker or series to backend/config/kalshi_market_discovery.json."
            status = "EMPTY"
        else:
            if preserved_snapshot:
                warnings.append("No active markets found in current fetch. Preserved previous valid snapshot.")
                status = "STALE"
            else:
                status = "OK"
                
        if final_selected and (known_markets or known_series) and not preserved_snapshot:
            next_action = "Known ticker tracking is active."

        snapshot = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
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
        
        if preserved_snapshot:
            # Write diagnostic artifact instead of overwriting latest
            failed_snapshot = {
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_EMPTY",
                "mode": "read_only_public_market_data",
                "base_url": client.base_url,
                "warnings": ["No active markets found in current fetch. Preserved previous valid snapshot."],
                "total_raw_markets_seen": raw_count,
                "candidate_markets_count": len(candidates),
                "selected_temperature_markets": [],
                "markets_found": 0
            }
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            filename = f"failed_kalshi_market_snapshot_{timestamp}.json"
            filepath = OUTPUT_DIR / filename
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(failed_snapshot, f, indent=2)
                print(f"Diagnostic artifact saved to: {filepath}")
            except Exception as e:
                print(f"Error writing diagnostic artifact: {e}")
                
            print("Preserved previous valid snapshot. Not overwriting latest.")
        else:
            saved_path = client.save_market_snapshot(snapshot, OUTPUT_DIR)
            print(f"\nSnapshot saved to: {saved_path}")
            
        print("Success.")
        
    except Exception as e:
        print(f"Error updating Kalshi snapshots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
