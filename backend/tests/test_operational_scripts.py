import os
import unittest

class TestOperationalScripts(unittest.TestCase):
    def setUp(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.scripts = [
            os.path.join(self.project_root, "scripts/generate_daily_status.sh"),
            os.path.join(self.project_root, "scripts/fetch_kalshi_markets.sh"),
            os.path.join(self.project_root, "scripts/run_kmia_daily_workflow.sh")
        ]

    def test_scripts_exist_and_executable(self):
        """Verify the scripts exist and are executable."""
        for script_path in self.scripts:
            self.assertTrue(os.path.exists(script_path), f"Script not found at {script_path}")
            self.assertTrue(os.access(script_path, os.X_OK), f"Script {script_path} is not executable")

    def test_scripts_safety_marker(self):
        """Verify the scripts contain the mandatory safety marker."""
        for script_path in self.scripts:
            with open(script_path, 'r') as f:
                content = f.read()
                self.assertIn("NO REAL TRADING EXECUTION", content)

    def test_scripts_no_forbidden_terms(self):
        """Verify the scripts do not contain forbidden trading execution terms or write methods."""
        forbidden = [
            "place_order", "submit_order", "create_order", "market_order", "cancel_order",
            "requests.post", "requests.put", "requests.patch", "requests.delete"
        ]
        for script_path in self.scripts:
            with open(script_path, 'r') as f:
                content = f.read()
                for term in forbidden:
                    self.assertNotIn(term, content, f"Forbidden term '{term}' found in script {script_path}")

    def test_daily_workflow_references_fetch_script(self):
        """Verify that run_kmia_daily_workflow.sh calls fetch_kalshi_markets.sh."""
        workflow_path = os.path.join(self.project_root, "scripts/run_kmia_daily_workflow.sh")
        with open(workflow_path, 'r') as f:
            content = f.read()
            self.assertIn("fetch_kalshi_markets.sh", content, "run_kmia_daily_workflow.sh does not call fetch_kalshi_markets.sh")

if __name__ == "__main__":
    unittest.main()
