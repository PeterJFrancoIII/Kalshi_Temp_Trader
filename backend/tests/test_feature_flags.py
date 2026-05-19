"""Tests for :mod:`shared.feature_flags` defaults and env-var parsing."""

import os
import unittest
from unittest import mock

from shared import feature_flags


class TestLLMReviewFlag(unittest.TestCase):
    def test_default_disabled(self):
        """The MVP must default to LLM review OFF."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k != feature_flags.LLM_REVIEW_ENABLED_ENV
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(feature_flags.is_llm_review_enabled())

    def test_truthy_values_enable_flag(self):
        for value in ("1", "true", "True", "yes", "ON", "y", "t"):
            with self.subTest(value=value):
                with mock.patch.dict(
                    os.environ,
                    {feature_flags.LLM_REVIEW_ENABLED_ENV: value},
                ):
                    self.assertTrue(feature_flags.is_llm_review_enabled())

    def test_unknown_value_treated_as_false(self):
        """Defensive: unknown strings (typos, garbage) must not enable."""
        for value in ("", "maybe", "0", "false", "no", "off", "banana"):
            with self.subTest(value=value):
                with mock.patch.dict(
                    os.environ,
                    {feature_flags.LLM_REVIEW_ENABLED_ENV: value},
                ):
                    self.assertFalse(feature_flags.is_llm_review_enabled())


if __name__ == "__main__":
    unittest.main()
