import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_feeds import FEEDS


class RunFeedsTests(unittest.TestCase):
    def test_feed_roster_is_the_four_rss_adapters(self):
        names = [name for name, _cls in FEEDS]
        self.assertEqual(
            names,
            [
                "matichon_news",
                "thai_business_news",
                "thai_tech_news",
                "notebookspec_tech",
            ],
        )


if __name__ == "__main__":
    unittest.main()
