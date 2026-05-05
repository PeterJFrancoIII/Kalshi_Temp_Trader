import os
import json
import shutil
import tempfile
import unittest
from calibration.generate_aggregate_report import main as generate_main

class TestGenerateAggregateReport(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "input")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.input_dir)
        os.makedirs(self.output_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_aggregate_with_files(self):
        # Create two valid comparison files
        comp1 = {
            "rules_v1": {"brier_score": 0.2, "log_loss": 0.5, "top_bin_hit": True, "actual_bin_probability": 0.6},
            "rules_v2_climatology": {"brier_score": 0.1, "log_loss": 0.4, "top_bin_hit": True, "actual_bin_probability": 0.7},
            "winner_by_brier": "rules_v2_climatology",
            "winner_by_log_loss": "rules_v2_climatology",
            "winner_by_top_bin": "tie",
            "brier_delta_v2_minus_v1": -0.1,
            "log_loss_delta_v2_minus_v1": -0.1
        }
        comp2 = {
            "rules_v1": {"brier_score": 0.3, "log_loss": 0.6, "top_bin_hit": False, "actual_bin_probability": 0.4},
            "rules_v2_climatology": {"brier_score": 0.2, "log_loss": 0.5, "top_bin_hit": True, "actual_bin_probability": 0.5},
            "winner_by_brier": "rules_v2_climatology",
            "winner_by_log_loss": "rules_v2_climatology",
            "winner_by_top_bin": "rules_v2_climatology",
            "brier_delta_v2_minus_v1": -0.1,
            "log_loss_delta_v2_minus_v1": -0.1
        }
        
        with open(os.path.join(self.input_dir, "comp1.json"), 'w') as f:
            json.dump(comp1, f)
        with open(os.path.join(self.input_dir, "comp2.json"), 'w') as f:
            json.dump(comp2, f)
            
        # Run main
        import sys
        from unittest.mock import patch
        test_args = ["prog", "--input-dir", self.input_dir, "--output-dir", self.output_dir]
        with patch.object(sys, 'argv', test_args):
            generate_main()
            
        # Verify output files
        json_out = os.path.join(self.output_dir, "aggregate_calibration.json")
        md_out = os.path.join(self.output_dir, "aggregate_calibration.md")
        
        self.assertTrue(os.path.exists(json_out))
        self.assertTrue(os.path.exists(md_out))
        
        with open(json_out, 'r') as f:
            stats = json.load(f)
            self.assertEqual(stats["settled_days"], 2)
            self.assertEqual(stats["v2_win_rate_by_brier"], 1.0)
            self.assertAlmostEqual(stats["v1_avg_brier"], 0.25)
            self.assertAlmostEqual(stats["v2_avg_brier"], 0.15)

    def test_empty_input_dir(self):
        import sys
        from unittest.mock import patch
        test_args = ["prog", "--input-dir", self.input_dir, "--output-dir", self.output_dir]
        with patch.object(sys, 'argv', test_args):
            generate_main()
            
        json_out = os.path.join(self.output_dir, "aggregate_calibration.json")
        self.assertTrue(os.path.exists(json_out))
        with open(json_out, 'r') as f:
            stats = json.load(f)
            self.assertEqual(stats["settled_days"], 0)
            self.assertIn("no comparison records", stats["warnings"])

    def test_malformed_json_skipped(self):
        # One valid, one malformed
        comp1 = {
            "rules_v1": {"brier_score": 0.2, "log_loss": 0.5, "top_bin_hit": True, "actual_bin_probability": 0.6},
            "rules_v2_climatology": {"brier_score": 0.1, "log_loss": 0.4, "top_bin_hit": True, "actual_bin_probability": 0.7},
            "winner_by_brier": "rules_v2_climatology",
            "winner_by_log_loss": "rules_v2_climatology",
            "winner_by_top_bin": "tie"
        }
        with open(os.path.join(self.input_dir, "valid.json"), 'w') as f:
            json.dump(comp1, f)
        with open(os.path.join(self.input_dir, "malformed.json"), 'w') as f:
            f.write("{ invalid json")
            
        import sys
        from unittest.mock import patch
        test_args = ["prog", "--input-dir", self.input_dir, "--output-dir", self.output_dir]
        with patch.object(sys, 'argv', test_args):
            generate_main()
            
        json_out = os.path.join(self.output_dir, "aggregate_calibration.json")
        with open(json_out, 'r') as f:
            stats = json.load(f)
            self.assertEqual(stats["settled_days"], 1)

    def test_script_executable(self):
        script_path = os.path.join(os.path.dirname(__file__), "../../scripts/generate_weekly_calibration.sh")
        script_path = os.path.abspath(script_path)
        self.assertTrue(os.path.exists(script_path))
        self.assertTrue(os.access(script_path, os.X_OK))

if __name__ == "__main__":
    unittest.main()
