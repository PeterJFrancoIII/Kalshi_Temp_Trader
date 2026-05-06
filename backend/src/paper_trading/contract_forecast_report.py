import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
SIGNAL_FILE = ROOT / "backend" / "data" / "processed" / "paper_trading" / "latest_paper_signal.json"
REPORTS_DIR = ROOT / "backend" / "data" / "processed" / "reports"

def generate_contract_forecast_report():
    """Generates a markdown report summarizing the active Kalshi contract forecasts."""
    if not SIGNAL_FILE.exists():
        logger.error(f"Signal file not found: {SIGNAL_FILE}")
        return None

    try:
        with open(SIGNAL_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading signal file: {e}")
        return None

    signals = data.get("signals", [])
    warnings = data.get("warnings", [])
    generated_at = data.get("generated_at_utc", "Unknown")
    
    # Format generated_at for display
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        display_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        display_time = generated_at

    md = []
    md.append("# Active Kalshi Contract Forecast Report")
    md.append(f"\n**Generated At:** {display_time}")
    md.append("\n> [!IMPORTANT]\n> **NO REAL TRADING EXECUTION.** This report is for paper trading evaluation only.\n")

    if warnings:
        md.append("\n## Warnings")
        for w in warnings:
            md.append(f"- {w}")

    md.append("\n## Active Contracts & Edge Analysis")
    
    if not signals:
        md.append("\nNo active contracts with valid model mappings found.")
    else:
        # Table Header
        header = "| Ticker | Contract | Status | Threshold | Model % | Market % | Edge | Speed-to-ROI | Action |"
        separator = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        md.append(header)
        md.append(separator)

        for s in signals:
            ticker = s.get("market_ticker", "N/A")
            title = s.get("market_title", "N/A")
            status = s.get("status", "N/A")
            threshold = f"{s.get('condition_type')} {s.get('threshold_f')}"
            model_p = f"{s.get('model_probability', 0)*100:.1f}%"
            market_p = f"{s.get('market_probability', 0)*100:.1f}%"
            edge = f"{s.get('edge', 0)*100:+.1f}%"
            speed = f"{s.get('speed_to_roi_score', 0):.2f}"
            action = s.get("paper_action", "WATCH")
            
            # Highlight interesting actions
            if "BUY" in action:
                action = f"**{action}**"

            row = f"| {ticker} | {title} | {status} | {threshold} | {model_p} | {market_p} | {edge} | {speed} | {action} |"
            md.append(row)

    md.append("\n## Safety Disclaimer")
    md.append("This system is a research MVP. All 'actions' and 'ROI' scores are purely hypothetical and intended for paper evaluation. The bot is strictly forbidden from executing real-money trades.")

    content = "\n".join(md)
    
    # Save report
    ts = datetime.now().strftime("%Y-%m-%d")
    latest_path = REPORTS_DIR / "latest_contract_forecast_report.md"
    ts_path = REPORTS_DIR / f"contract_forecast_report_{ts}.md"
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(latest_path, "w") as f:
        f.write(content)
    with open(ts_path, "w") as f:
        f.write(content)
        
    return latest_path

if __name__ == "__main__":
    path = generate_contract_forecast_report()
    if path:
        print(f"Contract forecast report generated at {path}")
