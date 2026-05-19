from typing import Dict, Optional
from datetime import datetime, timezone

def simulate_fill_from_snapshot(recommendation_record: Dict, market_snapshot: Dict) -> Dict:
    """
    Simulates a fill based on a recommendation and the current market snapshot.
    Updates the record with entry price and fills it.
    
    recommendation_record: The record created by save_recommendation
    market_snapshot: {
        "ticker": "...",
        "yes_ask": 45, # in cents
        "no_ask": 56,  # in cents
        "liquidity": 10
    }
    """
    if recommendation_record.get('recommendation_action') != 'TRADE_CANDIDATE':
        return recommendation_record

    side = recommendation_record.get('simulated_side', 'YES')
    
    # Simple logic: fill at the ask price if liquidity > 0
    if market_snapshot.get('liquidity', 0) > 0:
        entry_price = market_snapshot.get('yes_ask') if side == 'YES' else market_snapshot.get('no_ask')
        
        if entry_price is not None:
            recommendation_record['status'] = 'FILLED'
            recommendation_record['entry_price'] = entry_price
            recommendation_record['filled_at'] = datetime.now(timezone.utc).isoformat()
            recommendation_record['market_snapshot_at_fill'] = market_snapshot
    
    return recommendation_record

def settle_paper_trade(trade_record: Dict, actual_high: int) -> Dict:
    """
    Settles a filled paper trade based on the actual high temperature.
    
    trade_record: A record that has been 'FILLED'
    actual_high: The final ground truth high temperature.
    """
    if trade_record.get('status') != 'FILLED':
        return trade_record

    from paper_trading.settlement import contract_settles_yes
    is_hit = contract_settles_yes(actual_high, trade_record)

    side = trade_record.get('simulated_side', 'YES')
    entry_price = trade_record.get('entry_price', 0)
    
    # Calculate PnL
    # YES wins if is_hit is True
    # NO wins if is_hit is False
    if side == 'YES':
        settlement_value = 100 if is_hit else 0
    else: # NO
        settlement_value = 100 if not is_hit else 0
        
    pnl = settlement_value - entry_price
    
    trade_record['status'] = 'SETTLED'
    trade_record['settlement_result'] = 'WIN' if settlement_value == 100 else 'LOSS'
    trade_record['settlement_value'] = settlement_value
    trade_record['actual_high'] = actual_high
    trade_record['net_pnl'] = pnl
    trade_record['settled_at'] = datetime.now(timezone.utc).isoformat()
    
    return trade_record
