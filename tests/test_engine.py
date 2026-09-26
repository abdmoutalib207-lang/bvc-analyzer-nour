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

    def test_short_history_cannot_pass_full_readiness(self):
        result = analyze(FIXTURE["records"]["T2S"], ASOF)
        self.assertEqual(result["decision"], "LIMITÉ")
        self.assertEqual(result["quality"]["candles_in_extract"], 38)


if __name__ == "__main__":
    unittest.main()
