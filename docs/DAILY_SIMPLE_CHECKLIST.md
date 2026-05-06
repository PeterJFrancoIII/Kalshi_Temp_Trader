# Daily Simple Checklist

## 1. Open the console

Use the browser link.

## 2. Check the status color

See [What The Colors Mean](WHAT_THE_COLORS_MEAN.md).

* **GREEN**: Everything is working. Do nothing.
* **YELLOW**: Bot is working, but needs attention. Read the message.
* **RED**: Something is broken. Run `bash scripts/health_summary.sh`.

For monitoring simulated performance, see [Paper Trading Feedback](PAPER_TRADING_FEEDBACK.md).
For background loop status, see [Automated Paper Trading Loop](AUTOMATED_PAPER_LOOP.md).
For strategy lessons, see [Learning Summary](LEARNING_SUMMARY.md).
For data fixes, see [Manual Data Corrections](MANUAL_DATA_CORRECTIONS.md).
For live weather monitoring, see [Live NWS / KMIA Data](NWS_LIVE_DATA.md).

## 3. Safe commands

Run these from the server:

```bash
cd /opt/kmia-kalshi
source .venv/bin/activate

bash scripts/health_summary.sh
bash scripts/run_tests.sh
bash scripts/generate_daily_status.sh
bash scripts/update_kalshi_market_data.sh
bash scripts/generate_paper_signal.sh
bash scripts/record_paper_trade.sh
bash scripts/settle_paper_trades.sh
```

## 4. Git sync check

The codes on Mac and server should match.

Mac: `git rev-parse HEAD`
Server: `git rev-parse HEAD`

## 5. Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real orders.
