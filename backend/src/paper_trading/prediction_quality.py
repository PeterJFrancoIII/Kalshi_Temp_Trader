import json
import os
from datetime import datetime, timezone
from pathlib import Path

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

from shared.artifact_paths import PAPER_LEDGER_FILE
from paper_trading.paper_ledger import PaperLedger

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "backend" / "data" / "processed"
CONFIG_DIR = ROOT / "backend" / "config"

INPUT_PATHS = {
    "paper_signal": DATA_DIR / "paper_trading" / "latest_paper_signal.json",
    "paper_performance": DATA_DIR / "paper_trading" / "latest_paper_trading_performance.json",
    # Canonical production paper ledger (single JSON document).
    "paper_ledger": PAPER_LEDGER_FILE,
    "kalshi_snapshot": DATA_DIR / "kalshi_market_snapshots" / "latest_kalshi_market_snapshot.json",
    "status_dir": DATA_DIR / "status",
    "reports_dir": DATA_DIR / "reports",
    "manual_corrections": CONFIG_DIR / "manual_data_corrections.json"
}

OUTPUT_JSON = DATA_DIR / "learning" / "latest_prediction_quality_report.json"

def load_json(path):
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def get_latest_file(directory, pattern):
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def generate_report():
    generated_at = datetime.now(timezone.utc)
    trade_date = generated_at.strftime("%Y-%m-%d")
    
    # Load inputs
    paper_signal = load_json(INPUT_PATHS["paper_signal"])
    paper_perf = load_json(INPUT_PATHS["paper_performance"])
    kalshi_snapshot = load_json(INPUT_PATHS["kalshi_snapshot"])
    corrections = load_json(INPUT_PATHS["manual_corrections"])
    
    latest_status_json = get_latest_file(INPUT_PATHS["status_dir"], "kmia_daily_status_*.json")
    latest_forecast_md = get_latest_file(INPUT_PATHS["reports_dir"], "kmia_forecast_*.md")
    
    # Defaults
    quality = "REVIEW"
    main_risk = "Unknown"
    next_action = "Investigate missing data"
    data_quality_warnings = []
    notes = []
    manual_corrections_active = False
    excluded_dates = []
    
    # Evaluation logic
    if not latest_status_json or not latest_forecast_md:
        quality = "REVIEW"
        missing = []
        if not latest_status_json: missing.append("Daily status file")
        if not latest_forecast_md: missing.append("Forecast report")
        main_risk = f"Missing required files: {', '.join(missing)}"
        next_action = "Run kmia_daily_workflow.sh"
    elif corrections and "dates" in corrections and trade_date in corrections["dates"]:
        manual_corrections_active = True
        quality = "REVIEW"
        main_risk = f"Manual correction active for today ({trade_date})"
        next_action = "Review manual correction in config"
    else:
        # Check markets and signals
        markets_found = 0
        if kalshi_snapshot:
            markets_found = kalshi_snapshot.get("markets_found", 0)
            if markets_found == 0 and "markets" in kalshi_snapshot:
                markets_found = len(kalshi_snapshot["markets"])
        
        best_signal = None
        if paper_signal:
            best_signal = paper_signal.get("best_signal")
            
        if markets_found > 0 and best_signal:
            quality = "GOOD"
            main_risk = "None identified"
            next_action = "Monitor paper trading"
        elif markets_found == 0:
            quality = "WATCH"
            main_risk = "No Kalshi markets found for KMIA"
            next_action = "Wait for market discovery or check ticker config"
        else:
            quality = "WATCH"
            main_risk = "Kalshi markets found but no paper signal generated"
            next_action = "Review signal generation logs"

    # Special date checks (always check even if quality is already set)
    if corrections and "dates" in corrections:
        if "2026-05-05" in corrections["dates"]:
            if corrections["dates"]["2026-05-05"].get("exclude_from_learning"):
                data_quality_warnings.append("May 5 is excluded from learning.")
                excluded_dates.append("2026-05-05")
        
        if "2026-05-07" in corrections["dates"]:
            m_open = corrections["dates"]["2026-05-07"].get("market_open_time_et")
            if m_open:
                notes.append(f"May 7 market open time exists: {m_open} ET")

    # Pending settlements check (does not downgrade to REVIEW)
    pending_settlements = 0
    if paper_perf:
        pending_settlements = paper_perf.get("pending_trades", 0)
        
    # Extract forecast info for summary
    today_forecast = "N/A"
    top_probability_bin = "N/A"
    if latest_status_json:
        status_data = load_json(latest_status_json)
        if status_data:
            f_info = status_data.get("forecast", {})
            if not f_info:
                f_dict = status_data.get("forecasts", {})
                if isinstance(f_dict, dict) and f_dict:
                    f_info = next(iter(f_dict.values()))
            
            if isinstance(f_info, dict):
                today_forecast = f_info.get("best_single_number", "N/A")
                top_probability_bin = f_info.get("top_probability_bin", "N/A")

    # Paper signal info
    best_paper_signal = "None"
    if paper_signal and paper_signal.get("best_signal"):
        best_paper_signal = paper_signal["best_signal"].get("market_ticker", "Unknown")

    # Open paper trades — counted via the canonical PaperLedger so the value
    # actually reflects open positions (the legacy line-count approach
    # included settled/closed trades and silently returned 0 in production
    # because the JSONL file never existed there).
    open_paper_trades = 0
    if INPUT_PATHS["paper_ledger"].exists():
        try:
            open_paper_trades = PaperLedger(
                ledger_path=INPUT_PATHS["paper_ledger"]
            ).count_open_trades()
        except Exception:
            pass

    simulated_pnl = 0.0
    if paper_perf:
        simulated_pnl = paper_perf.get("total_simulated_pnl", 0.0)

    # Build report dict
    report = {
        "generated_at_utc": generated_at.isoformat(),
        "trade_date": trade_date,
        "prediction_quality": quality,
        "today_forecast": today_forecast,
        "top_probability_bin": top_probability_bin,
        "kalshi_markets_found": kalshi_snapshot.get("markets_found", 0) if kalshi_snapshot else 0,
        "best_paper_signal": best_paper_signal,
        "open_paper_trades": open_paper_trades,
        "pending_settlements": pending_settlements,
        "simulated_pnl": simulated_pnl,
        "data_quality_warnings": data_quality_warnings,
        "manual_corrections_active": manual_corrections_active,
        "excluded_from_learning_dates": excluded_dates,
        "main_risk": main_risk,
        "next_action": next_action,
        "notes": notes,
        "safety": {
            "no_real_trading": True,
            "disclaimer": "NO REAL TRADING EXECUTION - PAPER EVALUATION ONLY"
        }
    }

    # Ensure output dir exists
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(report, f, indent=2)
        
    # Save Markdown
    md_filename = f"prediction_quality_report_{trade_date}.md"
    md_path = OUTPUT_JSON.parent / md_filename
    
    md_content = f"""# Daily Prediction Quality Report: {trade_date}

**Status:** {quality}
**Main Risk:** {main_risk}
**Next Action:** {next_action}

## Prediction Details
- **Forecast:** {today_forecast}°F
- **Top Bin:** {top_probability_bin}
- **Kalshi Markets Found:** {report['kalshi_markets_found']}
- **Best Paper Signal:** {best_paper_signal}

## Paper Trading Summary
- **Open Trades:** {open_paper_trades}
- **Pending Settlements:** {pending_settlements}
- **Total Simulated PnL:** ${simulated_pnl:.2f}

## Data Quality & Corrections
- **Manual Corrections Active:** {"Yes" if manual_corrections_active else "No"}
- **Excluded from Learning:** {", ".join(excluded_dates) if excluded_dates else "None"}
"""

    if data_quality_warnings:
        md_content += "\n### Warnings\n"
        for w in data_quality_warnings:
            md_content += f"- {w}\n"
            
    if notes:
        md_content += "\n### Notes\n"
        for n in notes:
            md_content += f"- {n}\n"

    md_content += f"\n---\n*Generated at: {report['generated_at_utc']}*\n"
    md_content += "\n**NO REAL TRADING EXECUTION - PAPER EVALUATION ONLY**\n"

    with open(md_path, "w") as f:
        f.write(md_content)
        
    print(f"Report generated: {md_path}")
    return report

if __name__ == "__main__":
    generate_report()
