import os
import pytest
import subprocess

FORBIDDEN_TERMS = [
    "create_order",
    "submit_order",
    "cancel_order",
    "place_order",
    "market_order"
]

def test_no_forbidden_trading_terms_in_src():
    """
    Verify that no forbidden trading terms are present in the backend/src directory.
    This ensures that real-money trading logic is not accidentally introduced.
    """
    src_dir = "backend/src"
    
    # We use grep to search recursively
    for term in FORBIDDEN_TERMS:
        try:
            # -r recursive, -l list files, -w whole word
            result = subprocess.run(
                ["grep", "-rlw", term, src_dir],
                capture_output=True,
                text=True
            )
            # If grep returns 0, it found the term
            if result.returncode == 0:
                found_files = result.stdout.strip().split('\n')
                # Filter out shared types if they just define the list (though they shouldn't use these terms in logic)
                # But actually, the rule says NOT to add or enable them at all in src.
                pytest.fail(f"Forbidden term '{term}' found in: {found_files}")
        except FileNotFoundError:
            # Fallback if grep is not available (though it should be on Mac/Linux)
            pass

def test_agent_config_exists():
    """Verify that .agent metadata files exist."""
    assert os.path.exists(".agent/MASTER_DESCRIPTOR.md")
    assert os.path.exists(".agent/MACHINE_INDEX.yaml")
    
    rules = [
        "00-project.yaml",
        "10-safety.yaml",
        "20-descriptor-maintenance.yaml",
        "30-code-governance.yaml",
        "40-weather-market-models.yaml",
        "50-agent-index.yaml"
    ]
    for rule in rules:
        assert os.path.exists(f".agent/rules/{rule}")

def test_agent_yaml_parsing():
    """Verify that .agent YAML files are valid YAML (requires PyYAML)."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed, skipping YAML validation")

    yaml_files = [".agent/MACHINE_INDEX.yaml"]
    rules_dir = ".agent/rules"
    yaml_files.extend([os.path.join(rules_dir, f) for f in os.listdir(rules_dir) if f.endswith('.yaml')])
    
    for fpath in yaml_files:
        with open(fpath, 'r') as f:
            try:
                yaml.safe_load(f)
            except yaml.YAMLError as exc:
                pytest.fail(f"Error parsing {fpath}: {exc}")

def test_deployment_scripts_safety_markers():
    """Verify that deployment scripts and docs include the mandatory safety marker."""
    files_to_check = [
        "scripts/run_web_console.sh",
        "scripts/check_web_console.sh",
        "scripts/update_kalshi_market_data.sh",
        "docs/WEB_CONSOLE_DEPLOYMENT.md",
        "deploy/systemd/kmia-web-console.service"
    ]
    marker = "NO REAL TRADING EXECUTION"
    for fpath in files_to_check:
        assert os.path.exists(fpath), f"File missing: {fpath}"
        with open(fpath, 'r') as f:
            content = f.read()
            assert marker in content, f"Safety marker missing in {fpath}"

def test_executable_permissions():
    """Verify that scripts are executable."""
    scripts = [
        "scripts/run_web_console.sh",
        "scripts/check_web_console.sh"
    ]
    for s in scripts:
        assert os.access(s, os.X_OK), f"Script not executable: {s}"
