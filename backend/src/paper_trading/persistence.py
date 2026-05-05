import os
from typing import List, Optional, Dict
from storage.jsonl_store import JSONLStore

# Default path for paper trading records
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
