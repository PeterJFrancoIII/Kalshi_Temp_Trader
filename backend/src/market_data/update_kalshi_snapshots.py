import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from market_data.kalshi_public_client import KalshiPublicClient

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def main():
    print("--- Kalshi Public Market Data Updater ---")
    print("Mode: READ-ONLY / PAPER EVALUATION")
    
    client = KalshiPublicClient()
    
    # Target path
    # ROOT resolution assuming backend/src is in PYTHONPATH
    ROOT = Path(__file__).resolve().parents[3]
    OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "kalshi_market_snapshots"
    
    # Discovery terms
    query_terms = ["miami", "high"]
    print(f"Discovering markets for: {query_terms}...")
    
    try:
        markets = client.discover_temperature_markets(query_terms)
        print(f"Found {len(markets)} matching markets.")
        
        # Enrich with orderbooks for top markets if needed, 
        # but for now we focus on the list and basic prices in the market objects
        
        snapshot = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "base_url": client.base_url,
            "mode": "read_only_public_market_data",
            "query_terms": query_terms,
            "markets_found": len(markets),
            "markets": markets,
            "safety": {
                "no_real_trading": True,
                "no_order_execution": True,
                "disclaimer": "NO REAL TRADING EXECUTION - DRY-RUN ONLY"
            },
            "warnings": []
        }
        
        if not markets:
            snapshot["warnings"].append("No matching temperature markets found.")
            
        saved_path = client.save_market_snapshot(snapshot, OUTPUT_DIR)
        print(f"Snapshot saved to: {saved_path}")
        print("Success.")
        
    except Exception as e:
        print(f"Error updating Kalshi snapshots: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
