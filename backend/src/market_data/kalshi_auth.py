"""Kalshi read-only authentication helpers.

This module implements the RSA-PSS request signing required by the Kalshi API.
Due to the absence of the `cryptography` library in the environment and the
inability to install it (no internet), this implementation uses the `openssl`
command line tool via subprocess as a fallback.
"""

import base64
import os
import subprocess
import time
from typing import Dict


def get_required_env(name: str) -> str:
    """Get a required environment variable or fail closed."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_private_key_from_env() -> str:
    """Get the path to the RSA private key from environment.

    Fails closed if missing or file does not exist.
    """
    key_path = get_required_env("KALSHI_READ_ONLY_RSA_KEY_PATH")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"RSA key file not found at: {key_path}")
    return key_path


def sign_kalshi_request(
    private_key_path: str,
    timestamp_ms: str,
    method: str,
    path_without_query: str,
) -> str:
    """Sign a Kalshi request using OpenSSL.

    Payload: timestamp_ms + METHOD + path_without_query
    """
    payload = f"{timestamp_ms}{method}{path_without_query}"

    try:
        # Use openssl command line to sign
        process = subprocess.Popen(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sigopt",
                "rsa_padding_mode:pss",
                "-sign",
                private_key_path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=payload.encode("utf-8"))

        if process.returncode != 0:
            raise RuntimeError(
                f"OpenSSL signing failed: {stderr.decode('utf-8')}"
            )

        # Output of openssl dgst is the binary signature
        signature_base64 = base64.b64encode(stdout).decode("utf-8")
        return signature_base64

    except Exception as e:
        raise RuntimeError(f"Failed to sign request: {e}")


def create_kalshi_auth_headers(
    method: str, path_without_query: str
) -> Dict[str, str]:
    """Create authentication headers for a Kalshi request."""
    api_key_id = get_required_env("KALSHI_API_KEY_ID")
    private_key_path = load_private_key_from_env()

    # Kalshi expects timestamp in milliseconds
    timestamp_ms = str(int(time.time() * 1000))

    signature = sign_kalshi_request(
        private_key_path, timestamp_ms, method, path_without_query
    )

    return {
        "KALSHI-ACCESS-KEY": api_key_id,
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "KALSHI-ACCESS-SIGNATURE": signature,
    }
