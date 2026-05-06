import json
import os
from datetime import datetime, timezone
import glob

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data/processed")
PAPER_DIR = os.path.join(DATA_DIR, "paper_trading")
LEARNING_DIR = os.path.join(DATA_DIR, "learning")

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_open_trades_count():
    ledger_path = os.path.join(PAPER_DIR, "paper_trade_ledger.jsonl")
    count = 0
    if os.path.exists(ledger_path):
        with open(ledger_path, 'r') as f:
            for line in f:
                try:
                    trade = json.loads(line)
                    if trade.get('status') == 'open':
                        count += 1
                except:
                    continue
    return count

def generate_summary():
    os.makedirs(LEARNING_DIR, exist_ok=True)
    
    perf = load_json(os.path.join(PAPER_DIR, "latest_paper_trading_performance.json"))
    signal = load_json(os.path.join(PAPER_DIR, "latest_paper_signal.json"))
    
    settled_trades = perf.get('total_settled_trades', 0)
    win_rate = perf.get('win_rate', 0)
    simulated_pnl = perf.get('total_simulated_pnl', 0)
    pending_trades = perf.get('pending_trades', 0)
    
    # Model Lesson Rules
    if settled_trades == 0:
        model_lesson = "Waiting for settlement."
    elif win_rate >= 0.6:
        model_lesson = "Current paper strategy is performing well."
    elif win_rate < 0.5 and settled_trades >= 3:
        model_lesson = "Review calibration and edge thresholds."
    elif simulated_pnl < 0:
        model_lesson = "Paper strategy needs caution."
    else:
        model_lesson = "Collect more data."
        
    next_action = "Monitor upcoming market settlements."
    if settled_trades >= 3 and win_rate < 0.5:
        next_action = "Analyze losing trades for common patterns."
    
    best_sig = signal.get('best_signal', {})
    
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trade_date": signal.get('generated_at_utc', datetime.now(timezone.utc).isoformat())[:10],
        "latest_signal": best_sig.get('market_ticker', 'None'),
        "open_trades": get_open_trades_count(),
        "pending_trades": pending_trades,
        "settled_trades": settled_trades,
        "win_rate": win_rate,
        "simulated_pnl": simulated_pnl,
        "best_signal": best_sig,
        "model_lesson": model_lesson,
        "next_action": next_action,
        "safety": {
            "no_real_trading": True
        }
    }
    
    # Save latest
    latest_path = os.path.join(LEARNING_DIR, "latest_learning_summary.json")
    with open(latest_path, 'w') as f:
        json.dump(summary, f, indent=2)
        
    # Save daily
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    daily_path = os.path.join(LEARNING_DIR, f"daily_learning_summary_{today_str}.json")
    with open(daily_path, 'w') as f:
        json.dump(summary, f, indent=2)
        
    print(f"Learning summary generated: {latest_path}")
    return summary

if __name__ == "__main__":
    generate_summary()
