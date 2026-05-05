# Paper Trading Persistence

The Paper Trading system allows for the evaluation of Kalshi market recommendations without executing real trades. It persists simulated fill events and settlement results to a JSONL store.

## Storage

- **File**: `data/paper_trades.jsonl`
- **Format**: JSON Lines (JSONL), one record per line.

## Schema

### Recommendation Record

Initial record created when a recommendation is made.

```json
{
  "id": "uuid",
  "date": "2026-05-03",
  "forecast_summary": "High around 82F",
  "market_ticker": "KMIA-26MAY03-T81-82",
  "target_bin": "81-82",
  "recommendation_action": "TRADE_CANDIDATE",
  "simulated_side": "YES",
  "status": "PENDING",
  "created_at": "2026-05-03T18:00:00+00:00"
}
```

### Filled Record

Updated when a hypothetical fill occurs based on a market snapshot.

```json
{
  "status": "FILLED",
  "entry_price": 45,
  "filled_at": "2026-05-03T18:05:00Z",
  "market_snapshot_at_fill": { }
}
```

### Settled Record

Updated when the final high temperature is known.

```json
{
  "status": "SETTLED",
  "settlement_result": "WIN",
  "settlement_value": 100,
  "actual_high": 82,
  "net_pnl": 55,
  "settled_at": "2026-05-04T00:05:00Z"
}
```

## Functions

### `persistence.py`

- `save_recommendation(record)`: Appends a new record to the store.
- `load_recommendations(date=None)`: Retrieves records, optionally filtered by target date.
- `update_paper_trade(trade_id, updated_fields)`: Updates an existing record (e.g., to mark as FILLED or SETTLED).

### `simulator.py`

- `simulate_fill_from_snapshot(record, snapshot)`: Logic to determine if a trade would have been filled based on liquidity and price.
- `settle_paper_trade(record, actual_high)`: Logic to calculate PnL based on whether the final high temperature landed in the target bin.

## No Real Trading

> [!IMPORTANT]
> This module is strictly for simulation and evaluation. It contains no code to interact with the Kalshi API for order placement or account management.
