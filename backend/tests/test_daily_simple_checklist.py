import os
import unittest

class TestDailySimpleChecklist(unittest.TestCase):
    def setUp(self):
        self.checklist_path = os.path.join(os.getcwd(), "docs", "DAILY_SIMPLE_CHECKLIST.md")

    def test_checklist_exists(self):
        """Verify that docs/DAILY_SIMPLE_CHECKLIST.md exists."""
        self.assertTrue(os.path.exists(self.checklist_path), f"File not found: {self.checklist_path}")

    def test_checklist_content(self):
        """Verify the content of docs/DAILY_SIMPLE_CHECKLIST.md."""
        with open(self.checklist_path, "r") as f:
            content = f.read()
        
        self.assertIn("NO REAL TRADING EXECUTION", content)
        self.assertIn("GREEN", content)
        self.assertIn("YELLOW", content)
        self.assertIn("RED", content)
        self.assertIn("health_summary.sh", content)

if __name__ == "__main__":
    unittest.main()
