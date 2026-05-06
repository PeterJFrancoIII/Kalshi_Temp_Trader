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

if __name__ == "__main__":
    unittest.main()
