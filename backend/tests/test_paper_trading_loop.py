import os
from pathlib import Path

def test_paper_trading_loop_safety():
    """Verify script and systemd configurations for the paper trading loop."""
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "run_paper_trading_loop.sh"
    service_path = root / "deploy" / "systemd" / "kmia-paper-trading-loop.service"
    timer_path = root / "deploy" / "systemd" / "kmia-paper-trading-loop.timer"

    assert script_path.exists(), "run_paper_trading_loop.sh missing"
    assert service_path.exists(), "kmia-paper-trading-loop.service missing"
    assert timer_path.exists(), "kmia-paper-trading-loop.timer missing"

    content = script_path.read_text()
    assert "NO REAL TRADING EXECUTION" in content, "Safety disclaimer missing in script"
    
    service_content = service_path.read_text()
    assert "NO REAL TRADING EXECUTION" in service_content, "Safety disclaimer missing in service"
