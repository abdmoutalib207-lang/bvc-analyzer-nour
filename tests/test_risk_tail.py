import copy
import math
import unittest

from nour.risk_tail import historical_tail
from nour.research import risk, enrich
from nour.engine import build_report
from test_research import sample


class RiskTailTests(unittest.TestCase):
    def test_independent_nearest_rank_and_tail_mean(self):
        values = [i / 1000 for i in range(-60, 60)]
        result = historical_tail(values)
        self.assertEqual(result['observations'], 120)
        self.assertEqual(result['tail_observations'], 6)
        self.assertEqual(result['var95_loss_pct'], 5.5)
        self.assertEqual(result['cvar95_loss_pct'], 5.75)
        self.assertEqual(result['quantile05_return_pct'], -5.5)

    def test_boundary_119_insufficient_and_121_uses_seven(self):
        self.assertIsNone(historical_tail([-.01]*119)['var95_loss_pct'])
        self.assertEqual(historical_tail([-.01]*121)['tail_observations'], 7)

    def test_flat_and_positive_sample_do_not_report_negative_loss(self):
        for value in (0, .01):
            result = historical_tail([value]*120)
            self.assertEqual(result['var95_loss_pct'], 0)
            self.assertEqual(result['cvar95_loss_pct'], 0)
            self.assertIn('garantie', result['note'])

    def test_nonfinite_boolean_and_invalid_return_are_rejected(self):
        for value in (True, math.nan, math.inf, '0.1', -1, -2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                historical_tail([value]*120)

    def test_no_exchange_never_becomes_daily_return_or_bridged_gap(self):
        fixture, history, asof = sample()
        rec = fixture['records']['AAA']
        rec['candles'][-100]['v'] = 0
        out = risk(rec, history, asof)
        self.assertEqual(out['paired_returns'], 250)
        self.assertEqual(out['excluded_no_exchange_sessions'], 1)
        self.assertEqual(out['tail_risk']['observations'], 250)
        self.assertFalse(out['complete_window'])
        self.assertIsNone(out['drawdown_pct'])

    def test_only_trade_intervals_no_daily_var(self):
        fixture, history, asof = sample()
        rec = fixture['records']['AAA']
        rec['candles'] = rec['candles'][::2]
        out = risk(rec, history, asof)
        self.assertEqual(out['paired_returns'], 0)
        self.assertIsNone(out['tail_risk']['var95_loss_pct'])

    def test_suspension_and_short_resume_withhold_tail(self):
        fixture, history, asof = sample()
        for flags in ({'suspended': True}, {'resumed_recently': True, 'sessions_since_resume': 20},
                      {'resumed_recently': True, 'sessions_since_resume': True}):
            rec = {**fixture['records']['AAA'], **flags}
            out = risk(rec, history, asof)
            self.assertIsNone(out['tail_risk']['var95_loss_pct'])

    def test_future_bars_and_index_do_not_change_measures(self):
        fixture, history, asof = sample()
        before = risk(fixture['records']['AAA'], history, asof)
        fixture['records']['AAA']['candles'].append(dict(d='2099-01-01', o=1,h=1,l=1,c=1,v=1))
        history['2099-01-01'] = 1
        self.assertEqual(before, risk(fixture['records']['AAA'], history, asof))

    def test_enrichment_keeps_scores_technical_and_fundamentals_exact(self):
        fixture, history, asof = sample()
        report = build_report(fixture, asof)
        report['masi_history'] = history
        before = copy.deepcopy(report['results'])
        enrich(report, fixture)
        for a,b in zip(before, report['results']):
            for key in ('canonical_score', 'fundamental', 'technical', 'decision'):
                self.assertEqual(a[key], b[key])
            # Enrichment now aligns the frequency grid to the MASI calendar.
            # On this complete sample all numeric windows must remain exact;
            # only the explicitly documented horizon basis/note may change.
            self.assertEqual(a['historical_statistics']['horizons'], b['historical_statistics']['horizons'])
            self.assertEqual(a['historical_statistics']['first_session'], b['historical_statistics']['first_session'])
            self.assertEqual(a['historical_statistics']['last_session'], b['historical_statistics']['last_session'])
            self.assertEqual(b['historical_statistics']['horizon_basis'], 'market_calendar')
        self.assertEqual(report['results'][0]['market_risk']['tail_risk']['horizon_sessions'], 1)


if __name__ == '__main__':
    unittest.main()
