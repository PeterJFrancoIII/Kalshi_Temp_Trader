import os
import unittest

class TestOperationalScripts(unittest.TestCase):
    def setUp(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.script_path = os.path.join(self.project_root, "scripts/generate_daily_status.sh")

    def test_script_exists_and_executable(self):
        """Verify the status generation script exists and is executable."""
        self.assertTrue(os.path.exists(self.script_path), f"Script not found at {self.script_path}")
        self.assertTrue(os.access(self.script_path, os.X_OK), "Script is not executable")

    def test_script_safety_marker(self):
        """Verify the script contains the mandatory safety marker."""
        with open(self.script_path, 'r') as f:
            content = f.read()
            self.assertIn("NO REAL TRADING EXECUTION", content)

    def test_script_no_forbidden_terms(self):
        """Verify the script does not contain forbidden trading execution terms."""
        forbidden = ["place_order", "submit_order", "create_order", "market_order"]
        with open(self.script_path, 'r') as f:
            content = f.read()
            for term in forbidden:
                self.assertNotIn(term, content, f"Forbidden term '{term}' found in script")

if __name__ == "__main__":
    unittest.main()
