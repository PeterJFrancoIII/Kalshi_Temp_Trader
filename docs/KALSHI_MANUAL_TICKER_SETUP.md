# Kalshi Manual Ticker Setup

If auto-discovery finds 0 markets, you can manually add a known Kalshi market ticker or series ticker to track it.

## Instructions

1.  **Find the Ticker**: Go to Kalshi.com and find the Miami temperature market you want to track.
2.  **Edit Config**: Open [kalshi_market_discovery.json](file:///Users/computer/Desktop/App%20Development/Kalshi/backend/config/kalshi_market_discovery.json).
3.  **Add Market Ticker**:
    Add the ticker to `known_market_tickers`:
    ```json
    "known_market_tickers": ["HIGH-TEMP-MIA-26MAY26"]
    ```
4.  **Add Series Ticker**:
    Alternatively, add the series ticker to `known_series_tickers`:
    ```json
    "known_series_tickers": ["KXKX"]
    ```
5.  **Refresh Data**:
    Run the updater script:
    ```bash
    bash scripts/update_kalshi_market_data.sh
    ```
6.  **Verify**:
    Run the health summary:
    ```bash
    bash scripts/health_summary.sh
    ```

## Safety Notice
**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**
This system operates in read-only mode and does not require or support authentication or order execution.
