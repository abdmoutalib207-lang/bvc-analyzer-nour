import csv
import json
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from nour.engine import build_report
from nour.site import build_site, news_page

ROOT = Path(__file__).resolve().parents[1]


class VisibleMarketSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "data/market_snapshot.json").read_text())
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temporary.name)
        cls.asof = max(date.today().isoformat(), *(r.get("price_asof") or ""
                      for r in cls.fixture["records"].values()))
        facts = json.loads((ROOT / "data/facts_reference.json").read_text()).get("records", {})
        cls.report = build_report(cls.fixture, cls.asof, facts=facts)
        cls.report['market_overview'] = json.loads((ROOT/'data/market_overview.json').read_text())['current']
        cls.report['masi_history'] = json.loads((ROOT/'data/masi_history.json').read_text())['seances']
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

    def test_detail_keeps_chart_and_csv_without_expanded_history_table(self):
        page = (self.output / "titres/ADI.html").read_text()
        static = re.sub(r"<script\b[^>]*>.*?</script>", "", page, flags=re.DOTALL)
        self.assertIn('<polyline points="', static)
        self.assertIn('data-indicator="sma20"', static)
        self.assertIn('data-indicator="bands"', static)
        self.assertIn('data-indicator="rsi"', static)
        self.assertIn('data-indicator="macd"', static)
        self.assertIn('data-chart-type="candles"', static)
        self.assertNotIn("Dernières 40 séances", static)
        self.assertNotIn('<th>Ouverture</th>', static)
        self.assertIn('Historique à la demande', static)
        self.assertIn(self.fixture["records"]["ADI"]["candles"][-1]["d"], static)
        self.assertIn('href="../historique/ADI.csv"', static)

    def test_interactive_chart_carries_real_ohlcv_and_resumption_boundary(self):
        page = (self.output / "titres/ADI.html").read_text()
        payload = re.search(r'<script type="application/json" id="history-data">(.*?)</script>', page)
        self.assertIsNotNone(payload)
        bars = json.loads(payload.group(1))
        latest = self.fixture["records"]["ADI"]["candles"][-1]
        self.assertEqual(bars[-1], [latest[k] for k in ('d','o','h','l','c','v')])
        self.assertLessEqual(len(bars), len(self.fixture["records"]["ADI"]["candles"]))
        cmt = self.fixture["records"]["CMT"]
        recent = cmt["candles"][-cmt["sessions_since_resume"]]["d"]
        self.assertIn(f'data-indicator-since="{recent}"',
                      (self.output / "titres/CMT.html").read_text())
        self.assertNotIn('data-indicator="rsi"',
                         (self.output / "titres/DIS.html").read_text())

    def test_fundamental_colors_explain_sign_and_source_age(self):
        page = (self.output / "titres/ADI.html").read_text()
        self.assertIn('tone-neutral', page)
        self.assertIn('source-age', page)
        self.assertIn('Couleurs : proportion de points obtenus', page)
        self.assertIn('PER et P/B restent neutres', page)

    def test_both_explorers_bootstrap_and_preserve_index_observations(self):
        detail = (self.output / 'titres/ADI.html').read_text()
        market = (self.output / 'index.html').read_text()
        for page in (detail, market):
            self.assertLess(page.index('window.NourCharts={Viewport,mount}'),
                            page.index('new window.NourCharts.Viewport'))
        payload = re.search(r'<script type="application/json" id="masi-data">(.*?)</script>', market)
        self.assertIsNotNone(payload)
        expected = [[d, v] for d, v in sorted(self.report['masi_history'].items())
                    if d <= self.report['market_overview']['asof']]
        self.assertEqual(json.loads(payload.group(1)), expected)
        static = re.sub(r'<script\b[^>]*>.*?</script>', '', market, flags=re.DOTALL)
        self.assertIn('data-masi-chart', static)
        self.assertNotIn('data-chart-root', static)
        self.assertNotIn('data-chart-type="candles"', static)

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

    def test_news_lists_official_documents_before_secondary_off_topic_alerts(self):
        report = {"news": [
            {"tier":"S2", "title":"Concert au théâtre", "published_at":"2026-09-27", "url":"https://example.org/concert"},
            {"tier":"S1", "title":"Résultats d’un émetteur", "published_at":"2026-09-25", "url":"https://example.org/resultats"},
            {"tier":"S2", "title":"Dividende coté", "published_at":"2026-09-26", "url":"https://example.org/dividende"},
        ]}
        rendered = news_page(self.fixture, report, "", "")
        self.assertLess(rendered.index("Résultats d’un émetteur"), rendered.index("Dividende coté"))
        self.assertLess(rendered.index("Dividende coté"), rendered.index("Concert au théâtre"))
        self.assertIn("alertes à vérifier", rendered)


if __name__ == "__main__":
    unittest.main()
