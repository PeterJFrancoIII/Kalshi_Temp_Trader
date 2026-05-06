import os
import unittest

class TestOperatorColorDocs(unittest.TestCase):
    def setUp(self):
        self.doc_path = os.path.join(os.getcwd(), "docs", "WHAT_THE_COLORS_MEAN.md")

    def test_color_doc_exists(self):
        """Verify that docs/WHAT_THE_COLORS_MEAN.md exists."""
        self.assertTrue(os.path.exists(self.doc_path), f"File not found: {self.doc_path}")

    def test_color_doc_content(self):
        """Verify the content of docs/WHAT_THE_COLORS_MEAN.md."""
        with open(self.doc_path, "r") as f:
            content = f.read()
        
        self.assertIn("GREEN", content)
        self.assertIn("YELLOW", content)
        self.assertIn("RED", content)
        self.assertIn("NO REAL TRADING EXECUTION", content)

if __name__ == "__main__":
    unittest.main()
