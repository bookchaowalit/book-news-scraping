import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_feeds import FEEDS, run_feeds


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

    def test_one_failing_feed_does_not_block_the_others(self):
        class Broken:
            def __init__(self, **_kwargs):
                pass

            async def run(self):
                raise RuntimeError("publisher payload must not leak")

        class Working:
            def __init__(self, **_kwargs):
                pass

            async def run(self):
                return [{"source": "working", "count": 3}]

        with tempfile.TemporaryDirectory() as temp_dir:
            results = asyncio.run(
                run_feeds(Path(temp_dir), feeds=(("broken", Broken), ("working", Working)))
            )
        self.assertEqual(results[0], {"source": "broken", "error": "RuntimeError"})
        self.assertEqual(results[1]["count"], 3)


if __name__ == "__main__":
    unittest.main()
