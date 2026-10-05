import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from nour.engine import build_report
from nour.fundamentals import calculate
from nour.site import detail_page
from tools.reconcile_financial_oct05 import merge, SYMBOLS

ROOT = Path(__file__).resolve().parents[1]


class FinancialReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/facts_reference.json').read_text())
        cls.updated = merge(cls.data)

    def test_targeted_replay_and_semester_preservation(self):
        before = copy.deepcopy(self.data)
        after = merge(before)
        self.assertEqual(before, self.data)
        self.assertEqual(merge(after), after)
        for symbol, record in before['records'].items():
            if symbol not in SYMBOLS:
                self.assertEqual(record, after['records'][symbol])
            else:
                recent_before = record.get('latest_report') or {}
                recent_after = after['records'][symbol].get('latest_report') or {}
                if symbol != 'M2M':
                    self.assertEqual(recent_before, recent_after)
                else:
                    for field in ('document_url', 'period_end', 'reported_net_millions',
                                  'reported_net_previous_millions', 'revenue_millions', 'provenance'):
                        self.assertEqual(recent_before.get(field), recent_after.get(field))
        future = copy.deepcopy(before)
        for symbol in SYMBOLS:
            future['records'][symbol]['exercice'] = 2026
        self.assertEqual(merge(future), future)
        wrong = copy.deepcopy(before)
        wrong['records']['CDM']['url'] = 'https://example.org/other.pdf'
        with self.assertRaises(ValueError):
            merge(wrong)

    def test_cash_group_equity_and_closing_shares(self):
        self.assertEqual(245531 + 385425 - 82476 + 242296, 790776)
        self.assertEqual(781393 - (-8370 - 1013), 790776)
        self.assertEqual(Decimal('245530900') / 10, 24553090)
        self.assertEqual((2455309 - 2255309) * 10, 2000000)
        r = calculate({'price':200}, self.updated['records']['CASH'])
        self.assertEqual(r['eps_mad'], 9.87)
        self.assertEqual(r['roe_pct'], 30.64)
        self.assertIsNotNone(r['pb'])
        self.assertIsNone(r['net_debt_ebitda'])
        self.assertIn('indicatif', r['eps_denominator'])

    def test_eqdom_total_minus_minorities_rounding(self):
        self.assertEqual(1485722 + 717, 1486439)
        total = 167025 + 83325 + 1136829 + 99261
        self.assertEqual(total - (18 + 699) - 1485722, 1)
        r = calculate({'price':1000}, self.updated['records']['EQD'])
        self.assertEqual(r['roe_pct'], 6.63)
        self.assertEqual(r['book_value_per_share_mad'], 889.52)
        self.assertIsNotNone(r['pb'])

    def test_hal_ebe_and_financial_debt_not_all_noncurrent_liabilities(self):
        r = calculate({'price':60}, self.updated['records']['HAL'])
        self.assertEqual(1069960 + 313352 + 2121095 - 397799, 3106608)
        self.assertEqual(r['net_debt_strict_mmad'], 3106.61)
        self.assertEqual(r['net_debt_ebitda'], 5.91)
        self.assertAlmostEqual(r['earnings_mmad'], 99.83237679)
        self.assertEqual(r['eps_mad'], 1.98)
        self.assertEqual(r['evidence']['excedent_brut_exploitation']['value'], 525.676)
        self.assertTrue(self.updated['records']['HAL']['reconciliation_prior_annual'])

    def test_capital_change_keeps_historical_eps_not_current_market_ratios(self):
        for symbol, eps in [('HAL', 1.98), ('CDM', 79.36)]:
            r = calculate({'price':1000}, self.updated['records'][symbol])
            self.assertEqual(r['eps_mad'], eps)
            self.assertTrue(r['historical_per_share_only'])
            for key in ('pe', 'pb', 'dividend_yield_pct'):
                self.assertIsNone(r[key])
        for invalid in ({'period_end':'2026-12-31'}, {'valeur':True}, {'valeur':float('nan')},
                        {'valeur':-2}, {'valeur':1.2}, {'document_hash':'sha256:not-a-hash'}, {'page':False}, {'unite':'MMAD'},
                        {'url':'http://example.org/a.pdf'}, {'validation_status':'unverified'}):
            f = copy.deepcopy(self.updated['records']['CDM'])
            f['faits']['nombre_actions_annuel_verifie'].update(invalid)
            self.assertIsNone(calculate({'price':1000}, f)['eps_mad'])

    def test_m2m_total_never_becomes_group_result_or_strict_cash(self):
        f = self.updated['records']['M2M']
        r = calculate({'price':400}, f)
        self.assertEqual(r['earnings_mmad'], 5.305374)
        self.assertEqual(r['latest_report']['reported_net_millions'], 8.780283)
        self.assertIn('total', r['latest_report']['reported_net_label'])
        self.assertIn('aucune contradiction prouvée', r['latest_report']['note'])
        self.assertIsNone(r['net_debt_strict_mmad'])

    def test_mgl_existing_verified_amount_unchanged(self):
        f = self.updated['records']['MGL']
        self.assertEqual(1153383 + 148199 - 73362, 1228220)
        self.assertEqual(f['faits']['capitaux_propres_sociaux']['valeur'], 1228.22)
        self.assertEqual(f['faits'], self.data['records']['MGL']['faits'])

    def test_public_pages_explain_review_and_historical_perimeters(self):
        fixture = json.loads((ROOT / 'data/market_snapshot.json').read_text())
        report = build_report(fixture, '2026-10-05', facts=self.updated['records'])
        for symbol in SYMBOLS:
            item = next(r for r in report['results'] if r['symbol'] == symbol)
            page = detail_page(item, fixture['records'][symbol], fixture, '', '')
            self.assertIn('Rapprochement documentaire', page)
            self.assertIn('2026-10-05', page)
            if symbol in ('HAL', 'CDM'):
                self.assertIn('BPA historique 2025', page)
            if symbol == 'M2M':
                self.assertIn('RNPG S1 2026 non vérifié', page)
                self.assertNotIn('variation du résultat part du groupe', page)


if __name__ == '__main__':
    unittest.main()
