import os
import unittest
from unittest.mock import patch


class TestKalshiPublicClient(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("requests.get")
    def test_get_requests_include_auth_headers_when_enabled(self, mock_get):
        from market_data.kalshi_public_client import KalshiPublicClient

        # Mock responses
        mock_get.return_value.json.return_value = {"success": True}
        mock_get.return_value.raise_for_status.return_value = None

        # Enable auth via env var
        os.environ["KALSHI_USE_AUTH"] = "true"
        os.environ["KALSHI_API_KEY_ID"] = "test_id"
        
        with patch("market_data.kalshi_auth.load_private_key_from_env") as mock_load_key, \
             patch("market_data.kalshi_auth.sign_kalshi_request") as mock_sign:
            mock_load_key.return_value = "dummy_path"
            mock_sign.return_value = "dummy_signature"

            client = KalshiPublicClient()
            client._get("/test_path")

            # Verify requests.get was called with headers
            args, kwargs = mock_get.call_args
            headers = kwargs.get("headers")

            self.assertIn("KALSHI-ACCESS-KEY", headers)
            self.assertIn("KALSHI-ACCESS-TIMESTAMP", headers)
            self.assertIn("KALSHI-ACCESS-SIGNATURE", headers)

    @patch("requests.get")
    def test_get_requests_do_not_include_auth_headers_when_disabled(self, mock_get):
        from market_data.kalshi_public_client import KalshiPublicClient

        mock_get.return_value.json.return_value = {"success": True}
        mock_get.return_value.raise_for_status.return_value = None

        os.environ["KALSHI_USE_AUTH"] = "false"

        client = KalshiPublicClient()
        client._get("/test_path")

        args, kwargs = mock_get.call_args
        headers = kwargs.get("headers")

        self.assertNotIn("KALSHI-ACCESS-KEY", headers)

    def test_client_uses_default_base_url_if_env_missing(self):
        from market_data.kalshi_public_client import KalshiPublicClient

        client = KalshiPublicClient()
        self.assertEqual(client.base_url, "https://external-api.kalshi.com/trade-api/v2")

    def test_client_uses_env_base_url_if_provided(self):
        from market_data.kalshi_public_client import KalshiPublicClient

        os.environ["KALSHI_API_BASE_URL"] = "https://custom-api.kalshi.com"
        client = KalshiPublicClient()
        self.assertEqual(client.base_url, "https://custom-api.kalshi.com")

    def test_no_non_get_methods_exposed(self):
        from market_data.kalshi_public_client import KalshiPublicClient

        client = KalshiPublicClient()

        # Check that common non-GET methods are not there
        self.assertFalse(hasattr(client, "post"))
        self.assertFalse(hasattr(client, "put"))
        self.assertFalse(hasattr(client, "delete"))
        self.assertFalse(hasattr(client, "submit_order"))
        self.assertFalse(hasattr(client, "cancel_order"))


if __name__ == "__main__":
    unittest.main()
