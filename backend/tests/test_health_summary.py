import os
import stat
import re
from pathlib import Path

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def get_script_path():
    """Helper to find the script relative to the test location."""
    # Assuming tests run from backend/ directory
    return Path(os.getcwd()).parent / "scripts" / "health_summary.sh"

def test_health_summary_script_exists():
    """Verify that scripts/health_summary.sh exists."""
    script_path = get_script_path()
    assert script_path.exists(), f"{script_path} does not exist"

def test_health_summary_is_executable():
    """Verify that scripts/health_summary.sh is executable."""
    script_path = get_script_path()
    st = os.stat(script_path)
    assert bool(st.st_mode & stat.S_IXUSR), f"{script_path} is not executable"

def test_health_summary_safety_disclaimer():
    """Verify that the script contains the mandatory safety disclaimer."""
    script_path = get_script_path()
    content = script_path.read_text()
    assert "NO REAL TRADING EXECUTION" in content
    assert "DRY-RUN / PAPER EVALUATION ONLY" in content

def test_health_summary_no_dangerous_commands():
    """Verify that the script does not contain dangerous commands."""
    script_path = get_script_path()
    content = script_path.read_text()
    
    dangerous = [
        "rm -rf",
        "git reset",
        "git clean",
        "git push",
        "git commit"
    ]
    
    for cmd in dangerous:
        assert cmd not in content, f"Dangerous command '{cmd}' found in health_summary.sh"

def test_health_summary_read_only():
    """Verify that the script does not contain commands that modify files."""
    script_path = get_script_path()
    content = script_path.read_text()
    
    # Check for redirection or commands that might write
    # We allow redirects to /dev/null and 2>&1
    if ">" in content:
        # 1. Remove 2>&1
        sanitized = re.sub(r'2>&1', '', content)
        # 2. Remove redirects to /dev/null
        sanitized = re.sub(r'[12]?\s*>\s*/dev/null', '', sanitized)
        # 3. Check for any remaining >
        # We also want to ignore > in strings like "FINAL STATUS: ${STATUS_COLOR}" or similar
        # but the script uses echo -e, and > is not common in echo except for redirects.
        
        # Check if any > remains that is not part of a comparison like [[ $a -gt 0 ]] 
        # (bash uses -gt, not > for numeric comparison in [[ ]])
        # but for strings it might use >. Our script doesn't.
        
        assert ">" not in sanitized, f"Script might be writing to files. Remaining redirects: {re.findall(r'.{0,10}>.{0,10}', sanitized)}"
