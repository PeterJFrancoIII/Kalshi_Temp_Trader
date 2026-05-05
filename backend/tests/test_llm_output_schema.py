import unittest
from llm.llm_reviewer import validate_llm_review_output
from llm.consensus import compare_reviews

class TestLLMReviewLayer(unittest.TestCase):
    def test_validate_valid_output(self):
        output = {
            "best_single_number_f": 85,
            "probability_bins": {
                "<=78": 0.0,
                "79-80": 0.0,
                "81-82": 0.1,
                "83-84": 0.4,
                "85-86": 0.4,
                ">=87": 0.1
            },
            "confidence": "high"
        }
        self.assertTrue(validate_llm_review_output(output, 82))

    def test_validate_invalid_bins(self):
        # Missing bins
        output = {
            "probability_bins": {"<=78": 1.0},
            "confidence": "high"
        }
        with self.assertRaises(ValueError):
            validate_llm_review_output(output, 82)

    def test_validate_invalid_sum(self):
        # Sums to 1.1
        output = {
            "probability_bins": {
                "<=78": 0.1, "79-80": 0.2, "81-82": 0.2,
                "83-84": 0.2, "85-86": 0.2, ">=87": 0.2
            },
            "confidence": "high"
        }
        with self.assertRaisesRegex(ValueError, "Probabilities sum to"):
            validate_llm_review_output(output, 70)

    def test_validate_impossible_bin(self):
        output = {
            "probability_bins": {
                "<=78": 0.1, "79-80": 0.0, "81-82": 0.0,
                "83-84": 0.4, "85-86": 0.4, ">=87": 0.1
            },
            "confidence": "high"
        }
        # observed_max = 80, so <=78 is impossible
        with self.assertRaisesRegex(ValueError, "Bin <=78 must be 0"):
            validate_llm_review_output(output, 80)

    def test_compare_reviews_top_bin(self):
        rev_a = {
            "probability_bins": {"81-82": 0.8, "83-84": 0.2, "<=78":0, "79-80":0, "85-86":0, ">=87":0},
            "confidence": "high"
        }
        rev_b = {
            "probability_bins": {"81-82": 0.2, "83-84": 0.8, "<=78":0, "79-80":0, "85-86":0, ">=87":0},
            "confidence": "high"
        }
        flags = compare_reviews(rev_a, rev_b)
        self.assertTrue(any("Top bin disagreement" in f for f in flags))

    def test_compare_reviews_large_diff(self):
        rev_a = {
            "probability_bins": {"81-82": 0.5, "83-84": 0.5, "<=78":0, "79-80":0, "85-86":0, ">=87":0},
            "confidence": "high"
        }
        rev_b = {
            "probability_bins": {"81-82": 0.3, "83-84": 0.7, "<=78":0, "79-80":0, "85-86":0, ">=87":0},
            "confidence": "high"
        }
        # 0.5 - 0.3 = 0.2 (> 0.15)
        flags = compare_reviews(rev_a, rev_b)
        self.assertTrue(any("differs by >0.15" in f for f in flags))

    def test_compare_reviews_confidence(self):
        rev_a = {
            "probability_bins": {"81-82": 1.0, "83-84":0, "<=78":0, "79-80":0, "85-86":0, ">=87":0},
            "confidence": "high"
        }
        rev_b = {
            "probability_bins": {"81-82": 1.0, "83-84":0, "<=78":0, "79-80":0, "85-86":0, ">=87":0},
            "confidence": "low"
        }
        flags = compare_reviews(rev_a, rev_b)
        self.assertTrue(any("Confidence mismatch" in f for f in flags))

if __name__ == '__main__':
    unittest.main()
