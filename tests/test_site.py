import csv
import json
import re
import tempfile
import unittest
from pathlib import Path

from nour.engine import build_report
from nour.site import build_site

ROOT = Path(__file__).resolve().parents[1]


class VisibleMarketSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "data/market_snapshot.json").read_text())
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temporary.name)
        build_site(cls.fixture, build_report(cls.fixture, "2026-09-26"), cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_main_page_is_visible_with_scripts_disabled(self):
        page = (self.output / "index.html").read_text()
        static = re.sub(r"<script\b[^>]*>.*?</script>", "", page, flags=re.DOTALL)
        self.assertIn("80 valeurs", static)
        self.assertIn('<polyline points="', static)
        self.assertEqual(static.count('<tr data-market-row '), 80)
        self.assertIn('href="titres/ADI.html"', static)

    def test_each_ticker_has_a_real_page_and_csv_including_missing_histories(self):
        for symbol in self.fixture["symbols"]:
            detail = self.output / "titres" / f"{symbol}.html"
            csv_file = self.output / "historique" / f"{symbol}.csv"
            self.assertTrue(detail.is_file(), symbol)
            self.assertTrue(csv_file.is_file(), symbol)
            self.assertIn(symbol, detail.read_text())
        self.assertIn("Historique de cours indisponible", (self.output / "titres/DIS.html").read_text())
        with (self.output / "historique/ADI.csv").open(encoding="utf-8-sig") as fp:
            rows = list(csv.reader(fp, delimiter=";"))
        self.assertEqual(len(rows) - 1, 811)
        self.assertEqual(rows[-1][0], "2026-09-25")

    def test_static_detail_chart_and_recent_session_table(self):
        page = (self.output / "titres/ADI.html").read_text()
        static = re.sub(r"<script\b[^>]*>.*?</script>", "", page, flags=re.DOTALL)
        self.assertIn('<polyline points="', static)
        self.assertIn("Dernières 40 séances", static)
        self.assertIn("2026-09-25", static)
        self.assertIn('href="../historique/ADI.csv"', static)


if __name__ == "__main__":
    unittest.main()
