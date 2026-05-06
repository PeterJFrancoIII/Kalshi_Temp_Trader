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
    
    # ROOT resolution assuming backend/src is in PYTHONPATH
    # Path(__file__) is .../backend/src/market_data/update_kalshi_snapshots.py
    ROOT = Path(__file__).resolve().parents[3]
    CONFIG_PATH = ROOT / "backend" / "config" / "kalshi_market_discovery.json"
    OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "kalshi_market_snapshots"
    
    # Load Config
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "search_terms": ["miami", "high", "temperature"],
            "preferred_terms": ["miami", "high"]
        }

    search_terms = config.get("search_terms", [])
    preferred_terms = config.get("preferred_terms", [])
    
    client = KalshiPublicClient()
    print(f"Discovering markets using terms: {search_terms}...")
    
    try:
        # Broad discovery (ANY match)
        candidates = client.discover_temperature_markets(search_terms)
        print(f"Found {len(candidates)} total candidate markets.")
        
        # Refined selection (All preferred terms must match)
        selected = []
        for m in candidates:
            text = (f"{m.get('title', '')} {m.get('subtitle', '')} {m.get('ticker', '')}").lower()
            if all(pt.lower() in text for pt in preferred_terms):
                selected.append(m)
        
        print(f"Selected {len(selected)} matching Miami temperature markets.")
        
        next_action = "None. System is healthy."
        warnings = []
        if not selected:
            warnings.append("No matching Miami temperature markets found.")
            next_action = "No matching Kalshi Miami temperature market found. Review ticker/series manually."

        snapshot = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "base_url": client.base_url,
            "mode": "read_only_public_market_data",
            "search_terms_used": search_terms,
            "preferred_terms_used": preferred_terms,
            "total_markets_returned": len(candidates),
            "candidate_markets": candidates,
            "selected_temperature_markets": selected,
            "markets_found": len(selected), # Legacy field for compatibility
            "markets": selected,           # Legacy field for compatibility
            "safety": {
                "no_real_trading": True,
                "no_order_execution": True,
                "disclaimer": "NO REAL TRADING EXECUTION - DRY-RUN ONLY"
            },
            "warnings": warnings,
            "next_action": next_action
        }
        
        saved_path = client.save_market_snapshot(snapshot, OUTPUT_DIR)
        print(f"Snapshot saved to: {saved_path}")
        print("Success.")
        
    except Exception as e:
        print(f"Error updating Kalshi snapshots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
