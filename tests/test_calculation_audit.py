"""Independent oracle, publication tampering and inactive-session regressions."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import unittest

from nour.calculation_audit import audit_calculations
from nour.engine import build_report
from nour.research import enrich
from nour.statistics import describe
from nour.resilience import isolate_audit_failures, health_with_quarantines

ROOT = Path(__file__).resolve().parents[1]


def fixture(n=260):
    bars = []
    for i in range(n):
        c = 100 + i*.2 + (i % 9 - 4)*.7
        bars.append(dict(d=(date(2025, 1, 1)+timedelta(days=i)).isoformat(),
                         o=c-.1, h=c+1, l=c-1, c=c, v=100+i % 17))
    record = dict(symbol='TEST', name='Test', candles=bars,
                  price=bars[-1]['c'], price_asof=bars[-1]['d'])
    return dict(project='Test', symbols=['TEST'], records={'TEST': record},
                snapshot_updated=bars[-1]['d'], source_commit='test', source_files=[])


class StatisticalSessions(unittest.TestCase):
    def setUp(self):
        self.f = fixture(80)
        self.rec = self.f['records']['TEST']
        self.days = [b['d'] for b in self.rec['candles']]

    def counts(self, **kwargs):
        return [h['observations'] for h in describe(self.rec, sessions=self.days, **kwargs)['horizons']]

    def test_zero_volume_is_a_hole_not_a_zero_return_or_compressed_day(self):
        self.assertEqual(self.counts(), [79, 15, 3])
        self.rec['candles'][40]['v'] = 0
        self.assertEqual(self.counts(), [77, 13, 1])
        out = describe(self.rec, sessions=self.days)
        self.assertEqual(out['excluded_no_exchange_or_missing_sessions'], 1)
        for h in out['horizons']:
            self.assertEqual(h['candidate_windows'], h['observations']
                             + h['excluded_missing_or_inactive_windows'] + h['excluded_event_windows'])

    def test_missing_date_and_duplicate_date_break_fixed_calendar_windows(self):
        original = deepcopy(self.rec['candles'])
        self.rec['candles'].pop(40)
        self.assertEqual(self.counts(), [77, 13, 1])
        self.rec['candles'] = original + [deepcopy(original[40])]
        self.assertEqual(self.counts(), [77, 13, 1])
        self.assertEqual(describe(self.rec, sessions=self.days)['duplicate_sessions'], 1)

    def test_invalid_close_or_volume_is_not_an_observation(self):
        original = deepcopy(self.rec['candles'])
        for key, bad in [('c', True), ('c', float('inf')), ('c', -1),
                         ('v', True), ('v', None), ('v', -1), ('l', -1)]:
            with self.subTest(key=key, bad=bad):
                self.rec['candles'] = deepcopy(original)
                self.rec['candles'][40][key] = bad
                self.assertEqual(self.counts(), [77, 13, 1])

    def test_future_dates_cannot_shift_resumption_or_grid(self):
        self.rec.update(resumed_recently=True, sessions_since_resume=40)
        before = describe(self.rec, sessions=self.days, asof=self.days[-1])
        future = deepcopy(self.rec['candles'][-1]); future.update(d='2099-01-01', c=999)
        self.rec['candles'].append(future)
        self.assertEqual(before, describe(self.rec, sessions=self.days, asof=self.days[-1]))

    def test_event_boundary_and_suspension_are_excluded(self):
        self.assertEqual(self.counts(event_boundary=self.days[40]), [78, 14, 2])
        self.rec['suspended'] = True
        self.assertEqual(self.counts(), [0, 0, 0])


class CalculationAudit(unittest.TestCase):
    def setUp(self):
        self.f = fixture()
        self.report = build_report(self.f, self.f['snapshot_updated'])
        self.report['masi_history'] = {b['d']: b['c'] for b in self.f['records']['TEST']['candles']}
        enrich(self.report, self.f)

    def test_independent_decimal_matches_mixed_prices_and_no_mutation(self):
        before_f, before_r = deepcopy(self.f), deepcopy(self.report)
        result = audit_calculations(self.f, self.report)
        self.assertEqual(result['failures'], [])
        self.assertEqual(result['issuers_checked'], 1)
        self.assertGreater(result['arithmetic_checks'], 30)
        self.assertEqual(self.f, before_f)
        self.assertEqual(self.report, before_r)

    def test_corruption_or_missing_computable_indicator_is_blocking(self):
        for field in ('sma20', 'ema50', 'rsi14', 'macd_signal', 'atr14_wilder', 'bollinger_upper'):
            with self.subTest(field=field):
                report = deepcopy(self.report)
                report['results'][0]['technical'][field] += 1
                audit = audit_calculations(self.f, report)
                self.assertEqual(audit['status'], 'blocked')
                self.assertIn('technical.'+field, [f['metric'] for f in audit['failures']])
        self.report['results'][0]['technical']['sma20'] = None
        self.assertEqual(audit_calculations(self.f, self.report)['status'], 'blocked')

    def test_false_frequency_liquidity_or_universe_is_blocked(self):
        for section, field in [('liquidity', 'median_shares'), ('liquidity', 'exit_days_at_10pct')]:
            report = deepcopy(self.report)
            report['results'][0][section][field] += 1
            self.assertTrue(audit_calculations(self.f, report)['failures'])
        self.report['results'][0]['historical_statistics']['horizons'][0]['positive_frequency_pct'] = 999
        self.assertTrue(audit_calculations(self.f, self.report)['failures'])
        self.report['results'] = []
        self.assertEqual(audit_calculations(self.f, self.report)['status'], 'blocked')

    def test_percentiles_intervals_and_calendar_contract_are_independent(self):
        for field, value in [('p10_return_pct', 999), ('wilson95_pct', [0, 0])]:
            report = deepcopy(self.report)
            report['results'][0]['historical_statistics']['horizons'][0][field] = value
            self.assertTrue(audit_calculations(self.f, report)['failures'])
        report = deepcopy(self.report)
        report['results'][0]['historical_statistics']['event_boundary'] = '2099-01-01'
        self.assertTrue(audit_calculations(self.f, report)['failures'])
        report['results'][0]['historical_statistics']['horizons'] = []
        self.assertTrue(audit_calculations(self.f, report)['failures'])

    def test_all_eighty_issuers_on_the_repository_snapshot(self):
        f = json.loads((ROOT/'data/market_snapshot.json').read_text())
        self.assert_market_oracle(f)

    def test_five_source_quarantines_keep_healthy_arithmetic_strict(self):
        f=json.loads((ROOT/'data/market_snapshot.json').read_text())
        for symbol in ('ADH','ADI','IAM','MNG','STK'):
            f['records'][symbol]['quarantined_market']={
                'session':f['records'][symbol]['price_asof'],
                'reason':'Injected source contradiction'}
        report=self.assert_market_oracle(f)
        next(row for row in report['results'] if row['symbol']=='ADI')['technical']['sma20']=99999
        self.assertTrue(health_with_quarantines(audit_calculations(f,report),report)['failures'])

    def assert_market_oracle(self,f):
        # Financial arithmetic is separately controlled by publication_health;
        # every issuer's market arithmetic and every absence remain checked.
        asof=max(r.get('price_asof') or '' for r in f['records'].values())
        r = build_report(f, asof)
        r['masi_history'] = json.loads((ROOT/'data/masi_history.json').read_text())['seances']
        enrich(r, f)
        blocked={s for s,record in f['records'].items() if record.get('quarantined_market')}
        rows={row['symbol']:row for row in r['results']}
        healthy={s:deepcopy(row) for s,row in rows.items() if s not in blocked}
        for symbol in blocked:
            self.assertIsNone(rows[symbol]['price'])
            self.assertIsNone(rows[symbol]['technical']['sma20'])
        result = audit_calculations(f, r)
        self.assertEqual(result['universe'], 80)
        self.assertEqual(result['issuers_checked'], 80)
        # No healthy issuer's arithmetic may be excused by another quarantine.
        self.assertEqual([failure for failure in result['failures'] if failure['symbol'] not in blocked],[])
        isolate_audit_failures(r,result)
        checked=health_with_quarantines(audit_calculations(f,r),r)
        self.assertEqual(checked['failures'],[])
        for symbol,before in healthy.items():self.assertEqual(rows[symbol],before,symbol)
        if blocked:
            self.assertEqual(checked['status'],'degraded')
            self.assertTrue(checked['quarantined_failures'])
        return r



if __name__ == '__main__':
    unittest.main()
