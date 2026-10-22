"""Independent synthetic oracles for the publication volume safety net."""
import copy
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from nour.volume_guard import reconcile_volumes


DAY = "2026-10-16"
NOW = datetime(2026, 10, 18, 20, 0, tzinfo=timezone.utc)


def observations():
    records, raw, rows = {}, [], []
    for ticker, code, price, shares, amount in (("AAA", "XAA", 10, 10, "100.01"),
                                               ("BBB", "XBB", 20, 20, "400.02")):
        records[ticker] = {"price": price, "price_asof": DAY, "day_shares": shares,
                           "day_turnover_mad": float(amount),
                           "candles": [{"d": DAY, "o": price, "h": price + 1,
                                        "l": price - 1, "c": price, "v": shares}],
                           "archived_score": {"score": 42}, "untouched": [1, 2]}
        raw.append({"Symbol": code, "DateDernierCours": "16/10/2026 15:30", "Cours": price,
                    "Ouverture": price, "PlusHaut": price + 1, "PlusBas": price - 1,
                    "QteEchangee": shares, "Volumes": amount})
        rows.append({"symbol": code, "session": DAY, "price": price,
                     "amount_mad": amount, "shares": shares})
    fixture = {"records": records, "market": {"last_session": DAY}, "score_archive": ["never edit"]}
    overview = {"asof": DAY, "status": "closed", "turnover_mad": "500.03", "shares": 30,
                "breadth": {"quoted": 2}}
    secondary = {"provider": "Wafabourse", "status": "ok", "session": DAY,
                 "observed_at": "2026-10-18T19:00:00+00:00", "scope": "cash_equities",
                 "source_url": "https://www.wafabourse.com/marches", "market_closed": True,
                 "rows": rows, "notices": []}
    return fixture, raw, overview, secondary, {"AAA": "XAA", "BBB": "XBB"}


class VolumeGuardTests(unittest.TestCase):
    def run_guard(self, inputs, **kwargs):
        return reconcile_volumes(*inputs, now=kwargs.pop("now", NOW), minimum=kwargs.pop("minimum", 2), **kwargs)

    def assert_refused(self, inputs, **kwargs):
        before = copy.deepcopy(inputs)
        result, audit = self.run_guard(inputs, **kwargs)
        self.assertFalse(audit["publication_safe"], audit)
        self.assertEqual(result, before[0])
        self.assertEqual(inputs, before)
        self.assertEqual(audit["corrections"], [])
        return audit

    def test_exact_decimal_aggregate_and_full_quantity_quorum(self):
        inputs = observations()
        result, audit = self.run_guard(inputs)
        self.assertEqual(audit["status"], "matched")
        self.assertTrue(audit["publication_safe"])
        self.assertTrue(audit["cross_source_verified"])
        self.assertTrue(audit["quantities_cross_source_verified"])
        self.assertEqual(Decimal(audit["totals"]["candidate"]["turnover_mad"]), Decimal("500.03"))
        self.assertEqual(audit["totals"]["secondary"]["shares"], 30)
        self.assertEqual(result, inputs[0])
        result["records"]["AAA"]["untouched"].append(3)
        self.assertEqual(inputs[0]["records"]["AAA"]["untouched"], [1, 2])

    def test_volume_correction_is_transactional_idempotent_and_leaves_scores(self):
        inputs = observations()
        rec = inputs[0]["records"]["AAA"]
        rec.update(day_shares=9, day_turnover_mad=90)
        rec["candles"][0].update(v=9, turnover_mad=90)
        before = copy.deepcopy(inputs)
        result, audit = self.run_guard(inputs)
        self.assertEqual(audit["status"], "reconciled")
        self.assertEqual(audit["corrections"][0]["before"]["candle_shares"], 9)
        self.assertEqual(result["records"]["AAA"]["day_shares"], 10)
        self.assertEqual(result["records"]["AAA"]["candles"][0]["turnover_mad"], 100.01)
        self.assertEqual(result["score_archive"], before[0]["score_archive"])
        self.assertEqual(result["records"]["AAA"]["archived_score"], {"score": 42})
        self.assertEqual(inputs, before)
        rerun = (result, *inputs[1:])
        result2, audit2 = self.run_guard(rerun)
        self.assertEqual(result2, result)
        self.assertEqual(audit2["status"], "matched")
        self.assertEqual(audit2["corrections"], [])

    def test_amount_only_error_is_corrected_even_when_ohlcv_unchanged(self):
        inputs = observations()
        inputs[0]["records"]["AAA"]["day_turnover_mad"] = 90
        inputs[0]["records"]["AAA"]["candles"][0]["turnover_mad"] = 90
        result, audit = self.run_guard(inputs)
        self.assertEqual(audit["status"], "reconciled")
        self.assertEqual(result["records"]["AAA"]["day_turnover_mad"], 100.01)
        self.assertEqual(result["records"]["AAA"]["candles"][0]["v"], 10)

    def test_compensating_retained_errors_cannot_hide_behind_equal_total(self):
        inputs = observations()
        inputs[0]["records"]["AAA"]["day_turnover_mad"] = 110.01
        inputs[0]["records"]["BBB"]["day_turnover_mad"] = 390.02
        _, audit = self.run_guard(inputs)
        self.assertEqual(audit["status"], "reconciled")
        self.assertEqual(len(audit["corrections"]), 2)

    def test_compensating_second_provider_errors_are_refused_line_by_line(self):
        inputs = observations()
        inputs[3]["rows"][0]["amount_mad"] = "110.01"
        inputs[3]["rows"][1]["amount_mad"] = "390.02"
        audit = self.assert_refused(inputs)
        self.assertEqual(audit["status"], "conflict")
        self.assertFalse(audit["cross_source_verified"])

    def test_secondary_without_quantities_explains_single_source_quantity_limit(self):
        inputs = observations()
        for row in inputs[3]["rows"]:
            row["shares"] = None
        result, audit = self.run_guard(inputs)
        self.assertEqual(result["records"]["AAA"]["day_shares"], 10)
        self.assertTrue(audit["cross_source_verified"])
        self.assertFalse(audit["quantities_cross_source_verified"])
        self.assertIsNone(audit["totals"]["secondary"]["shares"])
        self.assertTrue(any("uniquement par CDG" in n for n in audit["notices"]))

    def test_missing_second_quantity_never_authorizes_a_quantity_revision(self):
        inputs=observations()
        for row in inputs[3]['rows']:
            row['shares']=None
        inputs[0]['records']['AAA']['day_shares']=9
        self.assert_refused(inputs)

    def test_secondary_amount_copied_as_shares_never_validates(self):
        inputs = observations()
        inputs[3]["rows"][0]["shares"] = 100
        self.assert_refused(inputs)

    def test_any_bad_ohlc_prevents_other_volume_correction(self):
        inputs = observations()
        inputs[0]["records"]["AAA"]["day_shares"] = 9
        inputs[0]["records"]["BBB"]["candles"][0]["o"] = 19
        self.assert_refused(inputs)

    def test_duplicate_and_missing_secondary_codes_and_dates_fail(self):
        for mutate in (lambda x: x[3]["rows"].append(copy.deepcopy(x[3]["rows"][0])),
                       lambda x: x[3]["rows"].pop(),
                       lambda x: x[3]["rows"][0].update(symbol="UNKNOWN"),
                       lambda x: x[3]["rows"][0].update(session="2026-10-15"),
                       lambda x: x[3].update(session="2026-10-15")):
            with self.subTest(mutate=mutate):
                inputs = observations()
                mutate(inputs)
                self.assert_refused(inputs)

    def test_cdg_duplicate_identity_collision_and_unmapped_trade_fail(self):
        for mutate in (lambda x: x[1].append(copy.deepcopy(x[1][0])),
                       lambda x: x[4].update(BBB="XAA"),
                       lambda x: x[1][0].update(Symbol="UNKNOWN")):
            with self.subTest(mutate=mutate):
                inputs = observations()
                mutate(inputs)
                self.assert_refused(inputs)

    def test_aggregate_quantity_count_or_amount_mismatch_fails(self):
        for mutate in (lambda x: x[2].update(shares=31),
                       lambda x: x[2].update(turnover_mad="500.05"),
                       lambda x: x[2]["breadth"].update(quoted=3)):
            inputs = observations()
            mutate(inputs)
            self.assert_refused(inputs)

    def test_future_cancelled_provisional_and_old_sessions_fail(self):
        for mutate in (lambda x: x[2].update(asof="2026-10-19"),
                       lambda x: x[2].update(asof="2026-09-17"),
                       lambda x: x[2].update(status="intraday"),
                       lambda x: x[2].update(provisional=True),
                       lambda x: x[0]["market"].update(last_session="2026-10-19"),
                       lambda x: x[3].update(market_closed=False),
                       lambda x: x[3].update(observed_at="2026-10-19T19:00:00+00:00")):
            inputs = observations()
            mutate(inputs)
            self.assert_refused(inputs)
        self.assert_refused(observations(), now=datetime(2026, 10, 16, 12, tzinfo=timezone.utc))

    def test_timeout_is_degraded_only_if_snapshot_already_matches(self):
        inputs = observations()
        inputs[3].update(status="timeout")
        result, audit = self.run_guard(inputs)
        self.assertEqual(audit["status"], "primary_checked")
        self.assertEqual(audit['secondary_status'], 'timeout')
        self.assertEqual(audit['publication_scope'], 'primary_only')
        self.assertTrue(audit["publication_safe"])
        self.assertFalse(audit["cross_source_verified"])
        self.assertEqual(result, inputs[0])
        inputs[0]["records"]["AAA"]["day_shares"] = 9
        self.assert_refused(inputs)

    def test_cdg_mirror_is_not_a_second_provider(self):
        for change in ({"provider": "CDG miroir"}, {"provider_id": "cdg"},
                       {"original_provider": "CDG Capital Bourse"},
                       {"source_url": "https://www.cdgcapitalbourse.ma/api/"}):
            inputs = observations()
            inputs[3].update(change)
            self.assert_refused(inputs)

    def test_invalid_units_noninteger_quantities_and_missing_candle_fail(self):
        for mutate in (lambda x: x[1][0].update(QteEchangee=10.5),
                       lambda x: x[1][0].update(Volumes="NaN"),
                       lambda x: x[3]["rows"][0].update(shares=True),
                       lambda x: x[0]["records"]["AAA"].update(candles=[])):
            inputs = observations()
            mutate(inputs)
            self.assert_refused(inputs)

    def test_minimum_twenty_is_default_in_production(self):
        inputs = observations()
        result, audit = reconcile_volumes(*inputs, now=NOW)
        self.assertFalse(audit["publication_safe"])
        self.assertEqual(audit["status"], "incomplete")
        self.assertEqual(result, inputs[0])

    def test_cdg_completely_empty_inactive_placeholder_is_not_an_error(self):
        inputs = observations()
        inactive = {"Symbol": "SUSP", "Cours": "", "DateDernierCours": "", "Volumes": "", "QteEchangee": ""}
        inputs[1].append(inactive)
        _, audit = self.run_guard(inputs)
        self.assertEqual(audit["status"], "matched")
        self.assertEqual(audit["totals"]["candidate"]["quoted"], 2)
        for contradictory in ({"Volumes": "50"}, {"Cours": 10}, {"DateDernierCours": "16/10/2026"},
                              {"QteEchangee": 0, "Volumes": 50}):
            case = copy.deepcopy(inputs)
            case[1][-1].update(contradictory)
            self.assert_refused(case)

    def test_extra_retained_amount_or_current_candle_cannot_escape_universe(self):
        for extra in ({"price_asof": DAY, "day_shares": 0, "day_turnover_mad": 100, "candles": []},
                      {"price_asof": "2026-10-15", "day_shares": 0, "day_turnover_mad": 0,
                       "candles": [{"d": DAY, "v": 1}]}):
            inputs = observations()
            inputs[0]["records"]["CCC"] = extra
            self.assert_refused(inputs)


if __name__ == "__main__":
    unittest.main()
