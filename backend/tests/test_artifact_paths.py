import unittest
from pathlib import Path
from shared.artifact_paths import (
    LATEST_KALSHI_MARKET_SNAPSHOT,
    LATEST_KALSHI_ORDERBOOKS,
    LATEST_PAPER_SIGNAL,
    LATEST_NWS_KMIA_SNAPSHOT
)

class TestArtifactPaths(unittest.TestCase):
    def test_artifact_paths(self):
        self.assertEqual(LATEST_KALSHI_MARKET_SNAPSHOT.name, "latest_kalshi_market_snapshot.json")
        self.assertEqual(LATEST_KALSHI_ORDERBOOKS.name, "latest_kalshi_orderbooks.json")
        self.assertEqual(LATEST_PAPER_SIGNAL.name, "latest_paper_signal.json")
        self.assertEqual(LATEST_NWS_KMIA_SNAPSHOT.name, "latest_nws_kmia_snapshot.json")

if __name__ == "__main__":
    unittest.main()
