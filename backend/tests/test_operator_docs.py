import os
import unittest

class TestOperatorDocs(unittest.TestCase):
    def setUp(self):
        self.docs_path = os.path.join(os.getcwd(), "docs", "TROUBLESHOOTING_SIMPLE.md")

    def test_troubleshooting_doc_exists(self):
        """Verify that docs/TROUBLESHOOTING_SIMPLE.md exists."""
        self.assertTrue(os.path.exists(self.docs_path), f"File not found: {self.docs_path}")

    def test_troubleshooting_doc_content(self):
        """Verify the content of docs/TROUBLESHOOTING_SIMPLE.md."""
        with open(self.docs_path, "r") as f:
            content = f.read()
        
        self.assertIn("NO REAL TRADING EXECUTION", content)
        self.assertIn("kmia-web-console.service", content)
        self.assertIn("health_summary.sh", content)
        self.assertIn("check_sync_status.sh", content)

    def test_paper_trading_doc_exists(self):
        """Verify that docs/PAPER_TRADING_FEEDBACK.md exists."""
        self.assertTrue(os.path.exists(os.path.join(os.getcwd(), "docs", "PAPER_TRADING_FEEDBACK.md")))

    def test_paper_trading_doc_content(self):
        """Verify the content of docs/PAPER_TRADING_FEEDBACK.md."""
        with open(os.path.join(os.getcwd(), "docs", "PAPER_TRADING_FEEDBACK.md"), "r") as f:
            content = f.read()
        self.assertIn("NO REAL TRADING EXECUTION", content)
        self.assertIn("PAPER SIGNAL", content)
        self.assertIn("SETTLED TRADE", content)
        self.assertIn("simulated", content)

    def test_automated_paper_loop_doc_exists(self):
        """Verify that docs/AUTOMATED_PAPER_LOOP.md exists."""
        self.assertTrue(os.path.exists(os.path.join(os.getcwd(), "docs", "AUTOMATED_PAPER_LOOP.md")))

    def test_automated_paper_loop_doc_content(self):
        """Verify the content of docs/AUTOMATED_PAPER_LOOP.md."""
        with open(os.path.join(os.getcwd(), "docs", "AUTOMATED_PAPER_LOOP.md"), "r") as f:
            content = f.read()
        self.assertIn("NO REAL TRADING EXECUTION", content)
        self.assertIn("paper-only", content)
        self.assertIn("run_paper_trading_loop.sh", content)
        self.assertIn("kmia-paper-trading-loop.timer", content)

    def test_deploy_guide_exists(self):
        """Verify that docs/DEPLOY_SIMPLE.md exists."""
        self.assertTrue(os.path.exists(os.path.join(os.getcwd(), "docs", "DEPLOY_SIMPLE.md")))

    def test_deploy_guide_content(self):
        """Verify the content of docs/DEPLOY_SIMPLE.md."""
        with open(os.path.join(os.getcwd(), "docs", "DEPLOY_SIMPLE.md"), "r") as f:
            content = f.read()
        self.assertIn("NO REAL TRADING EXECUTION", content)
        self.assertIn("deploy_from_mac.sh", content)
        self.assertIn("ssh kmia", content)

if __name__ == "__main__":
    unittest.main()
