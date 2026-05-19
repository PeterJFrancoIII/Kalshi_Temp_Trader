"""Generic JSONL-backed recommendation store (legacy / utility).

This module is NOT the production paper ledger. The canonical production
paper account lives in :mod:`paper_trading.paper_ledger` (PaperLedger,
backed by ``ledger.json``). The helpers here predate that and remain only
as a generic append/read/update JSONL primitive used by older unit tests.

For new code:
    - To record or query paper trades, use
      :class:`paper_trading.paper_ledger.PaperLedger`.
    - To persist arbitrary JSONL records, instantiate
      :class:`storage.jsonl_store.JSONLStore` directly with an explicit path.

Scheduled to be removed once the legacy tests migrate. Do not add new
callers.

NO REAL TRADING EXECUTION.
"""

import os
from typing import List, Optional, Dict
from storage.jsonl_store import JSONLStore

# Default path for the legacy JSONL store. Kept only so the existing tests
# pass without modification; production code reads ledger.json via
# PaperLedger.
DEFAULT_STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data',
    'paper_trades.jsonl'
)

def get_store(path: str = DEFAULT_STORAGE_PATH) -> JSONLStore:
    return JSONLStore(path)

def save_recommendation(record: Dict, path: str = DEFAULT_STORAGE_PATH):
    """
    Saves a recommendation record to the paper trade store.
    
    Expected record structure:
    {
        "id": "uuid or unique string",
        "date": "YYYY-MM-DD",
        "forecast_summary": "...",
        "market_ticker": "...",
        "recommendation_action": "TRADE_CANDIDATE",
        "simulated_side": "YES",
        "status": "PENDING",
        "created_at": "ISO-timestamp"
    }
    """
    store = get_store(path)
    store.append_record(record)

def load_recommendations(date: Optional[str] = None, path: str = DEFAULT_STORAGE_PATH) -> List[Dict]:
    """
    Loads recommendation records, optionally filtered by date.
    """
    store = get_store(path)
    records = store.load_records()
    if date:
        return [r for r in records if r.get('date') == date]
    return records

def update_paper_trade(trade_id: str, updated_fields: Dict, path: str = DEFAULT_STORAGE_PATH) -> bool:
    """
    Updates an existing paper trade record by its ID.
    """
    store = get_store(path)
    return store.update_record('id', trade_id, updated_fields)
