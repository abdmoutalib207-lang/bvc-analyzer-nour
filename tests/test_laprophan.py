"""A new listing enters collection without synthetic history or inherited ratios."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import unittest

from nour.assistant import build_data
from nour.engine import build_report
from nour.market import CASABLANCA, capture_intraday, import_session
from nour.resilience import validate_fixture
from nour.sector_methods import guidance
from nour.site import detail_page

ROOT = Path(__file__).resolve().parents[1]


class LaprophanTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((ROOT/'data/market_snapshot.json').read_text())
        self.codes = json.loads((ROOT/'data/source_codes.json').read_text())
        self.facts = json.loads((ROOT/'data/facts_reference.json').read_text())['records']

    def test_identity_and_first_sessions_are_explicit_without_ipo_price_candle(self):
        validate_fixture(self.fixture, self.codes)
        self.assertIn('LPH', self.fixture['symbols'])
        self.assertEqual(self.codes['LPH'], 'LPH')
        r = self.fixture['records']['LPH']
        self.assertEqual(r['isin'], 'MA0000012882')
        self.assertEqual(r['listing']['first_session'], '2026-11-25')
        self.assertEqual(r['listing']['subscription_price_mad'], 341)
        self.assertEqual(r['candles'][0], dict(d='2026-11-25', o=305, h=333, l=300, c=300, v=358274))
        self.assertTrue(all(b['d'] >= '2026-11-25' for b in r['candles']))
        self.assertEqual(guidance('LPH')['family'], guidance('SOT')['family'])
        self.assertNotEqual(guidance('LPH')['family'], guidance('JET')['family'])

    def test_short_history_and_fundamentals_preserve_existing_thresholds(self):
        f = deepcopy(self.fixture)
        rec = f['records']['LPH']
        rec['candles'] = [b for b in rec['candles'] if b['d'] <= '2026-11-26']
        rec.update(price=310, price_asof='2026-11-26', stale=False)
        rec.pop('quarantined_market', None)
        report = build_report(f, '2026-11-27', facts=self.facts)
        row = next(r for r in report['results'] if r['symbol'] == 'LPH')
        self.assertEqual(row['decision'], 'LIMITÉ')
        self.assertEqual(row['technical']['sessions'], 2)
        for key in ('sma20', 'sma50', 'sma200', 'rsi14', 'atr14'):
            self.assertIsNone(row['technical'][key], key)
        for key in ('eps_mad', 'pe', 'pb', 'roe_pct'):
            self.assertIsNone(row['fundamental'][key], key)
        self.assertIsNone(row['canonical_score']['value'])
        self.assertFalse(row['liquidity']['ready'])
        self.assertEqual(build_data(report)['symbols']['LPH']['listing'], rec['listing'])
        page = detail_page(row, rec, f, '', '')
        self.assertIn('id="introduction"', page)
        self.assertIn('MA0000012882', page)
        self.assertIn('341,00 MAD', page)
        self.assertIn(rec['history_provenance']['source_sha256'], page)
        # Adding LPH cannot change any previous issuer's calculations.
        f['symbols'].remove('LPH'); f['records'].pop('LPH')
        before = build_report(f, '2026-11-27', facts=self.facts)
        self.assertEqual(before['results'], [r for r in report['results'] if r['symbol'] != 'LPH'])

    def test_live_lph_observation_is_provisional_then_imported_after_close(self):
        fixture = deepcopy(self.fixture)
        fixture['symbols'] = ['LPH']; fixture['records'] = {'LPH': fixture['records']['LPH']}
        r = fixture['records']['LPH']
        r['candles'] = [b for b in r['candles'] if b['d'] <= '2026-11-26']
        r.update(price=310, price_asof='2026-11-26')
        day = '30/11/2026'
        line = dict(Symbol='LPH', DateDernierCours=day+' 15:30:00',
                    Cours=311, Ouverture=310, PlusHaut=312, PlusBas=309,
                    QteEchangee=100, Volumes=31100)
        before = deepcopy(fixture)
        point = capture_intraday(fixture, [line], {'LPH':'LPH'},
                                 now=datetime(2026,11,30,12,tzinfo=CASABLANCA))
        self.assertTrue(point['quotes']['LPH']['provisional'])
        self.assertEqual(fixture, before)
        with self.assertRaises(ValueError):
            import_session(fixture, [line], {'LPH':'LPH'}, minimum=1,
                           now=datetime(2026,11,30,12,tzinfo=CASABLANCA))
        after, audit = import_session(fixture, [line], {'LPH':'LPH'}, minimum=1,
                                     now=datetime(2026,11,30,17,tzinfo=CASABLANCA))
        self.assertEqual(audit['new_bars'], 1)
        self.assertEqual(after['records']['LPH']['price'], 311)
        self.assertEqual(after['records']['LPH']['listing'], r['listing'])
        self.assertEqual(fixture, before)
