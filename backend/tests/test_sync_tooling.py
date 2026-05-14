import subprocess
import os

def test_scripts_contain_safety_disclaimer():
    """
    Ensure all sync and deployment scripts contain the NO REAL TRADING EXECUTION disclaimer.
    """
    scripts_to_check = [
        "scripts/check_sync_status.sh",
        "scripts/update_server_from_github.sh",
        "docs/SYNC_WORKFLOW.md"
    ]
    
    disclaimer = "NO REAL TRADING EXECUTION"
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    for script_path in scripts_to_check:
        full_path = os.path.join(project_root, script_path)
        assert os.path.exists(full_path), f"{full_path} does not exist"
        
        with open(full_path, "r") as f:
            content = f.read()
            assert disclaimer in content, f"{script_path} missing mandatory disclaimer: {disclaimer}"

def test_check_sync_status_runs():
    """
    Ensure scripts/check_sync_status.sh runs without error on the local environment.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    script_path = os.path.join(project_root, "scripts/check_sync_status.sh")
    result = subprocess.run(["bash", script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"check_sync_status.sh failed with stderr: {result.stderr}"
    assert "KMIA Sync Status Checker" in result.stdout
    assert "NO REAL TRADING EXECUTION" in result.stdout
