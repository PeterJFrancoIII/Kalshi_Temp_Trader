import unittest
import os

class TestDeploymentAssets(unittest.TestCase):
    def setUp(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.scripts_dir = os.path.join(self.project_root, "scripts")
        self.deploy_dir = os.path.join(self.project_root, "deploy/systemd")

    def test_scripts_exist_and_executable(self):
        scripts = ["linux_setup.sh", "health_check.sh"]
        for script in scripts:
            path = os.path.join(self.scripts_dir, script)
            self.assertTrue(os.path.exists(path), f"Script missing: {path}")
            self.assertTrue(os.access(path, os.X_OK), f"Script not executable: {path}")

    def test_systemd_files_exist(self):
        files = [
            "kmia-daily-workflow.service", "kmia-daily-workflow.timer",
            "kmia-status.service", "kmia-status.timer",
            "kmia-health-check.service", "kmia-health-check.timer"
        ]
        for f in files:
            path = os.path.join(self.deploy_dir, f)
            self.assertTrue(os.path.exists(path), f"Systemd file missing: {path}")

    def test_safety_markers_in_deployment_files(self):
        # Check all .sh in scripts and all files in deploy/systemd
        dirs_to_check = [self.scripts_dir, self.deploy_dir]
        for d in dirs_to_check:
            for f in os.listdir(d):
                if f.endswith(".sh") or f.endswith(".service") or f.endswith(".timer"):
                    path = os.path.join(d, f)
                    with open(path, 'r') as file:
                        content = file.read()
                        self.assertIn("NO REAL TRADING EXECUTION", content, f"Safety marker missing in {f}")

    def test_no_forbidden_terms_in_deployment_assets(self):
        forbidden = ["create_order", "submit_order", "cancel_order", "place_order", "market_order", "ENABLE_REAL_TRADING"]
        dirs_to_check = [self.scripts_dir, self.deploy_dir]
        for d in dirs_to_check:
            for f in os.listdir(d):
                if f.endswith(".sh") or f.endswith(".service") or f.endswith(".timer"):
                    path = os.path.join(d, f)
                    with open(path, 'r') as file:
                        content = file.read()
                        for term in forbidden:
                            self.assertNotIn(term, content, f"Forbidden term '{term}' found in {f}")

if __name__ == "__main__":
    unittest.main()
