import csv
import json
import re
import tempfile
import unittest
from datetime import date
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
        cls.asof = max(date.today().isoformat(), *(r.get("price_asof") or ""
                      for r in cls.fixture["records"].values()))
        cls.report = build_report(cls.fixture, cls.asof)
        build_site(cls.fixture, cls.report, cls.output)

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
        candles = self.fixture["records"]["ADI"]["candles"]
        self.assertEqual(len(rows) - 1, len(candles))
        self.assertEqual(rows[-1][0], candles[-1]["d"])

    def test_static_detail_chart_and_recent_session_table(self):
        page = (self.output / "titres/ADI.html").read_text()
        static = re.sub(r"<script\b[^>]*>.*?</script>", "", page, flags=re.DOTALL)
        self.assertIn('<polyline points="', static)
        self.assertIn("Dernières 40 séances", static)
        self.assertIn(self.fixture["records"]["ADI"]["candles"][-1]["d"], static)
        self.assertIn('href="../historique/ADI.csv"', static)

    def test_csv_matches_snapshot_and_published_quality_counts(self):
        """The audit counters and each warning must describe exported rows."""
        self.assertEqual(len(self.fixture["symbols"]), 80)
        self.assertEqual(set(self.fixture["records"]), set(self.fixture["symbols"]))
        by_symbol = {r["symbol"]: r for r in self.report["results"]}
        for symbol in self.fixture["symbols"]:
            candles = self.fixture["records"][symbol]["candles"]
            with (self.output / "historique" / f"{symbol}.csv").open(encoding="utf-8-sig") as fp:
                rows = list(csv.DictReader(fp, delimiter=";"))
            self.assertEqual(len(rows), len(candles), symbol)
            dates = [r["Séance"] for r in rows]
            self.assertEqual(dates, sorted(set(dates)), symbol)
            self.assertTrue(all(date.fromisoformat(d) <= date.fromisoformat(self.asof) for d in dates), symbol)
            self.assertEqual(sum(r["Contrôle OHLC"] == "Ouverture hors fourchette" for r in rows),
                             by_symbol[symbol]["quality"]["invalid_open_count"], symbol)
            self.assertEqual(sum(r["Contrôle OHLC"] == "Clôture hors fourchette" for r in rows),
                             by_symbol[symbol]["quality"]["invalid_close_count"], symbol)


if __name__ == "__main__":
    unittest.main()
