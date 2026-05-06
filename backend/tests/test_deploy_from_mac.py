import os
from pathlib import Path

def test_deploy_from_mac_safety():
    """Verify safety constraints in deploy_from_mac.sh."""
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "deploy_from_mac.sh"

    assert script_path.exists(), "deploy_from_mac.sh missing"

    content = script_path.read_text()
    
    # Must contain
    assert "NO REAL TRADING EXECUTION" in content, "Safety disclaimer missing"
    assert "ssh kmia" in content, "SSH command missing"
    assert "git push origin main" in content, "Git push command missing"
    
    # Must NOT contain unsafe operations
    assert "rsync" not in content, "UNSAFE: Contains rsync"
    assert "git reset" not in content, "UNSAFE: Contains git reset"
    assert "git clean" not in content, "UNSAFE: Contains git clean"
    assert "git add ." not in content, "UNSAFE: Contains git add . instead of specific paths"
    
    # Must specifically mention excluded paths
    assert "backend/data/processed" in content, "Missing exclusion for processed data"
    assert "backend/tests/temp" in content, "Missing exclusion for test temp data"

