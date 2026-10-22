import json
import unittest
from copy import deepcopy
from pathlib import Path

from nour.engine import analyze, build_report

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "data/pilot_snapshot.json").read_text())
ASOF = "2026-09-26"


class EngineContract(unittest.TestCase):
    def test_pilot_fixture_is_complete_and_snapshot_matches_last_close(self):
        report = build_report(FIXTURE, ASOF)
        self.assertEqual(len(report["results"]), 8)
        self.assertEqual([r["symbol"] for r in report["results"]], FIXTURE["symbols"])
        for r in report["results"]:
            self.assertFalse(any("Désaccord" in issue for issue in r["quality"]["issues"]))
            self.assertIn(r["decision"], {"OBSERVABLE", "LIMITÉ", "INDISPONIBLE", "SUSPENDU"})
            self.assertEqual(r["decision_type"], "data_readiness_only")
            self.assertNotIn("buy", r)
            self.assertNotIn("sig", r)

    def test_actual_ohlc_defect_is_reported_without_fabricating_high_low(self):
        report = build_report(FIXTURE, ASOF)
        by_symbol = {r["symbol"]: r for r in report["results"]}
        self.assertGreater(by_symbol["RDS"]["quality"]["invalid_open_count"], 0)
        self.assertGreater(by_symbol["SMI"]["quality"]["invalid_open_count"], 0)
        self.assertEqual(by_symbol["ADI"]["quality"]["invalid_open_count"], 0)
        self.assertEqual(by_symbol["SMI"]["decision"], "LIMITÉ")

    def test_recent_resumption_does_not_mix_pre_and_post_suspension_liquidity(self):
        cmt = analyze(FIXTURE["records"]["CMT"], ASOF)
        self.assertEqual(cmt["liquidity"]["window_sessions"], 7)
        self.assertTrue(cmt["liquidity"]["post_resume_only"])
        self.assertFalse(cmt["liquidity"]["ready"])
        self.assertIsNone(cmt["liquidity"]["exit_days_at_10pct"])
        self.assertFalse(cmt["trend"]["ready"])

    def test_invalid_resume_count_cannot_borrow_pre_suspension_liquidity(self):
        for count in (None, True, 0, -1, '26'):
            with self.subTest(count=count):
                rec = deepcopy(FIXTURE['records']['ADI'])
                rec.update(resumed_recently=True, sessions_since_resume=count)
                item = analyze(rec, ASOF)
                self.assertEqual(item['liquidity']['window_sessions'], 0)
                self.assertFalse(item['liquidity']['ready'])
                self.assertIsNone(item['liquidity']['capacity_shares_per_session_at_10pct'])

    def test_boolean_snapshot_price_is_never_a_one_dirham_quote(self):
        rec = deepcopy(FIXTURE['records']['ADI'])
        for bar in rec['candles']:
            bar.update(o=1, h=1, l=1, c=1)
        rec['price'] = True
        item = analyze(rec, ASOF)
        self.assertEqual(item['decision'], 'INDISPONIBLE')

    def test_stale_or_inconsistent_snapshot_blocks_capacity_and_direction(self):
        stale = deepcopy(FIXTURE["records"]["ADI"])
        stale["price_asof"] = "2026-09-10"
        result = analyze(stale, ASOF)
        self.assertEqual(result["decision"], "INDISPONIBLE")
        self.assertFalse(result["liquidity"]["ready"])
        wrong = deepcopy(FIXTURE["records"]["ADI"])
        wrong["price"] = 1
        self.assertEqual(analyze(wrong, ASOF)["decision"], "INDISPONIBLE")

    def test_untrusted_close_outside_range_is_not_used(self):
        wrong = deepcopy(FIXTURE["records"]["ADI"])
        wrong["candles"][-2]["c"] = wrong["candles"][-2]["h"] + 100
        result = analyze(wrong, ASOF)
        self.assertEqual(result["quality"]["invalid_close_count"], 1)
        self.assertEqual(result["quality"]["rejected_bars"], 1)
        self.assertEqual(result["decision"], "LIMITÉ")

    def test_malformed_quote_date_and_nonfinite_price_are_safe(self):
        for bad_date in ('not-a-date', '2026-99-99'):
            rec = deepcopy(FIXTURE['records']['ADI'])
            rec['price_asof'] = bad_date
            result = analyze(rec, ASOF)
            self.assertEqual(result['decision'], 'INDISPONIBLE')
            self.assertIn('Date de cours illisible', result['quality']['issues'])
            self.assertFalse(result['liquidity']['ready'])
        for bad_price in (float('nan'), float('inf'), 10 ** 1000, 'invalid'):
            rec = deepcopy(FIXTURE['records']['ADI'])
            rec['price'] = bad_price
            result = analyze(rec, ASOF)
            self.assertEqual(result['decision'], 'INDISPONIBLE')
            self.assertFalse(result['liquidity']['ready'])
        rec = deepcopy(FIXTURE['records']['ADI'])
        rec['candles'][-1]['c'] = 10 ** 1000
        result = analyze(rec, ASOF)
        self.assertTrue(result['quality']['rejected_bars'] >= 1)

    def test_rejected_market_quote_cannot_produce_pe_or_pb(self):
        facts = json.loads((Path(__file__).resolve().parents[1] /
                            'data/facts_reference.json').read_text())['records']
        rec = deepcopy(FIXTURE['records']['ADI'])
        rec['price'] = 1
        fixture = deepcopy(FIXTURE)
        fixture['records']['ADI'] = rec
        # The pilot snapshot predates the current imported facts. Re-anchor
        # the snapshot for this regression without changing annual evidence.
        fixture['snapshot_updated'] = '2026-10-16T00:00:00'
        report = build_report(fixture, '2026-10-16', facts=facts)
        item = next(x for x in report['results'] if x['symbol'] == 'ADI')
        self.assertEqual(item['decision'], 'INDISPONIBLE')
        self.assertIsNone(item['fundamental']['pe'])
        self.assertIsNone(item['fundamental']['pb'])
        self.assertIsNotNone(item['fundamental']['earnings_mmad'])

    def test_full_report_survives_oversized_candle_and_excludes_it(self):
        fixture = deepcopy(FIXTURE)
        fixture['records']['ADI']['candles'][-1]['c'] = 10 ** 1000
        report = build_report(fixture, ASOF)
        item = next(x for x in report['results'] if x['symbol'] == 'ADI')
        self.assertGreaterEqual(item['quality']['rejected_bars'], 1)
        self.assertLess(item['technical']['sessions'],
                        len(fixture['records']['ADI']['candles']))

    def test_short_history_cannot_pass_full_readiness(self):
        result = analyze(FIXTURE["records"]["T2S"], ASOF)
        self.assertEqual(result["decision"], "LIMITÉ")
        self.assertEqual(result["quality"]["candles_in_extract"], 38)


if __name__ == "__main__":
    unittest.main()
