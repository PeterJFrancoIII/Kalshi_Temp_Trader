import os
from pathlib import Path

def test_start_entire_system_safety():
    """Verify safety constraints in start_entire_system.sh."""
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "start_entire_system.sh"

    assert script_path.exists(), "start_entire_system.sh missing"

    content = script_path.read_text()
    
    # Must contain
    assert "NO REAL TRADING EXECUTION" in content, "Safety disclaimer missing"
    assert "health_summary.sh" in content, "health_summary.sh missing"
    assert "kmia-web-console.service" in content, "Web console service restart missing"
    
    # Must NOT contain unsafe git operations
    assert "git push" not in content, "UNSAFE: Contains git push"
    assert "git reset" not in content, "UNSAFE: Contains git reset"
    assert "git clean" not in content, "UNSAFE: Contains git clean"
