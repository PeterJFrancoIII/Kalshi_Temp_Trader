# Real Trading Gate — Not Approved

## Current status: real trading NOT approved
The KMIA Predictor system is strictly authorized for **research, dry-run forecasting, and paper evaluation only**. No real-money trading execution is implemented or permitted in the current architecture.

## Why real trading is out of scope
The system currently relies on:
- Preliminary NWS sensor data (prone to calibration shifts).
- JSONL-based storage (lacking transactional integrity).
- Unauthenticated public API endpoints.
- Non-deterministic orderbook timing.

## Minimum evidence required before discussion
Transitioning to real-money execution requires a separate project phase and a rigorous audit. No discussion of real trading will be entertained until the following evidence is collected over a consistent period:
- **Calibration Stability**: At least 30 settled daily forecasts with stable Brier and Log Loss metrics.
- **Paper Performance**: At least 30 settled paper recommendations showing positive simulated net PnL after accounting for the Kalshi fee formula and bid/ask spreads.
- **Data Reliability**: No parser failures or missing data reports for at least 2 consecutive weeks.
- **False Positive Control**: No "stale-data" false positives or "missing-temp" errors for at least 2 weeks.
- **Manual Review**: A documented manual-review process for daily forecasts must be established.

## Required technical controls before any real trading architecture
If a real trading phase is approved, the following technical controls must be implemented *before* any execution logic is written:
- **Hard Persistence**: Migration from JSONL to a transactional database (SQLite or Postgres).
- **Time Normalization**: Full UTC timestamp normalization across all data sources.
- **Audit Logging**: Comprehensive, append-only audit logs for all market interactions.
- **Kill Switch**: A global, easily accessible emergency stop to halt all execution.
- **Risk Caps**: Hard-coded limits on maximum daily loss and maximum per-trade risk.
- **Security Review**: Full security review of authenticated API interactions and credential handling.

## Required human controls
- **Manual Approval Mode**: Any initial real trading must require manual one-click approval before order submission.
- **Double-Entry Verification**: Secondary verification of price and bin mapping before transmission.

## Required safety controls
- **Feature Flags**: Order placement code must be isolated behind a disabled-by-default feature flag.
- **No Market Orders**: Automation must strictly use limit orders; market orders are forbidden in automated paths to prevent slippage.

## Explicitly forbidden until approval
The following functions, modules, and flows are strictly forbidden in the codebase:
- `create_order`
- `submit_order`
- `cancel_order`
- `place_order`
- `market_order`
- Authenticated Kalshi trading client (using private keys or session tokens).
- Private key or API secret handling.
- Automatic real-money execution paths.

> [!CAUTION]
> Attempting to bypass these gates or introduce trading logic without a formal architecture review is a violation of project safety governance.
