import base64
import os
import subprocess
import unittest
from unittest.mock import patch


class TestKalshiAuth(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {})
        self.env_patcher.start()

        # Create a dummy key for testing
        self.test_key_path = "backend/tests/test_key.pem"
        subprocess.run(
            ["openssl", "genrsa", "-out", self.test_key_path, "2048"],
            capture_output=True,
        )

    def tearDown(self):
        self.env_patcher.stop()
        if os.path.exists(self.test_key_path):
            os.remove(self.test_key_path)

    def test_missing_api_key_id_raises_error(self):
        from market_data.kalshi_auth import get_required_env

        with self.assertRaises(ValueError):
            get_required_env("KALSHI_API_KEY_ID")

    def test_missing_key_path_raises_error(self):
        from market_data.kalshi_auth import load_private_key_from_env

        os.environ["KALSHI_API_KEY_ID"] = "test_id"
        # KALSHI_READ_ONLY_RSA_KEY_PATH is missing
        with self.assertRaises(ValueError):
            load_private_key_from_env()

    def test_nonexistent_key_path_raises_error(self):
        from market_data.kalshi_auth import load_private_key_from_env

        os.environ["KALSHI_API_KEY_ID"] = "test_id"
        os.environ["KALSHI_READ_ONLY_RSA_KEY_PATH"] = "nonexistent_path.pem"
        with self.assertRaises(FileNotFoundError):
            load_private_key_from_env()

    def test_signature_generation_returns_base64(self):
        from market_data.kalshi_auth import sign_kalshi_request

        os.environ["KALSHI_API_KEY_ID"] = "test_id"
        os.environ["KALSHI_READ_ONLY_RSA_KEY_PATH"] = self.test_key_path

        signature = sign_kalshi_request(
            self.test_key_path,
            "1710000000000",
            "GET",
            "/trade-api/v2/markets",
        )

        # Check if it's base64
        try:
            base64.b64decode(signature)
            is_base64 = True
        except Exception:
            is_base64 = False

        self.assertTrue(is_base64)
        self.assertTrue(len(signature) > 0)

    def test_auth_headers_contain_required_fields(self):
        from market_data.kalshi_auth import create_kalshi_auth_headers

        os.environ["KALSHI_API_KEY_ID"] = "test_id"
        os.environ["KALSHI_READ_ONLY_RSA_KEY_PATH"] = self.test_key_path

        headers = create_kalshi_auth_headers("GET", "/trade-api/v2/markets")

        self.assertIn("KALSHI-ACCESS-KEY", headers)
        self.assertIn("KALSHI-ACCESS-TIMESTAMP", headers)
        self.assertIn("KALSHI-ACCESS-SIGNATURE", headers)
        self.assertEqual(headers["KALSHI-ACCESS-KEY"], "test_id")

    @patch("builtins.print")
    def test_auth_helper_does_not_print_key_contents(self, mock_print):
        from market_data.kalshi_auth import sign_kalshi_request

        os.environ["KALSHI_API_KEY_ID"] = "test_id"
        os.environ["KALSHI_READ_ONLY_RSA_KEY_PATH"] = self.test_key_path

        sign_kalshi_request(
            self.test_key_path,
            "1710000000000",
            "GET",
            "/trade-api/v2/markets",
        )

        # Verify print was not called
        mock_print.assert_not_called()


if __name__ == "__main__":
    unittest.main()
