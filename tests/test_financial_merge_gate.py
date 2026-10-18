"""Merge gate: calculations are selective, auditable and safe for 80 symbols.

This test intentionally does not require all 80 issuers to have a certified
RNPG or P/E. Missing primary evidence is a valid unavailable state, never a
reason to synthesize figures.
"""
import copy
import json
import unittest
from pathlib import Path

from nour.engine import build_report
from nour.fundamentals import calculate

ROOT = Path(__file__).resolve().parents[1]


class FinancialMergeGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / 'data/market_snapshot.json').read_text())
        cls.facts = json.loads((ROOT / 'data/facts_reference.json').read_text())['records']
        cls.asof = max('2026-10-16', cls.fixture['snapshot_updated'][:10])
        cls.report = build_report(cls.fixture, cls.asof, facts=cls.facts)
        cls.items = {r['symbol']: r for r in cls.report['results']}

    def test_all_80_symbols_are_present_and_missing_reports_are_explicit(self):
        self.assertEqual(len(self.items), 80)
        self.assertEqual(set(self.items), set(self.fixture['symbols']))
        self.assertGreaterEqual(len(self.facts), 77)
        for symbol in set(self.items) - set(self.facts):
            f = self.items[symbol]['fundamental']
            self.assertIsNone(f['eps_mad'])
            self.assertIsNone(f['pe'])
            self.assertIsNone(f['roe_pct'])

    def test_metric_availability_matches_the_actual_values(self):
        for symbol, item in self.items.items():
            with self.subTest(symbol=symbol):
                f = item['fundamental']
                availability = f['metric_availability']
                blocked = set(f['financial_audit']['blocked_metrics'])
                for metric, info in availability.items():
                    self.assertIn(info['status'], ('available', 'unavailable', 'blocked'))
                    self.assertEqual(info['status'] == 'blocked', metric in blocked)
                    self.assertEqual(info['status'] == 'available', f.get(metric) is not None)
                    if info['status'] == 'blocked':
                        self.assertIsNone(f.get(metric))
                self.assertEqual(f['coverage_pct'],
                    25 * sum(f.get(k) is not None for k in
                             ('eps_mad', 'pb', 'roe_pct', 'revenue_growth_pct')))

    def test_unverified_consolidated_total_is_not_group_net(self):
        for symbol in ('TGCC', 'SGTM', 'CMGP'):
            with self.subTest(symbol=symbol):
                unresolved = copy.deepcopy(self.facts[symbol])
                unresolved['faits'] = copy.deepcopy(unresolved.get('reconciliation_prior_oct18', unresolved['faits']))
                unresolved.pop('calculation_reservations', None)
                f = calculate(self.fixture['records'][symbol], unresolved, asof=self.asof)
                self.assertIn('resultat_net_consolide', f['evidence'])
                self.assertIsNone(f['earnings_mmad'])
                self.assertIsNone(f['eps_mad'])
                self.assertIsNone(f['pe'])
                self.assertIsNone(f['roe_pct'])

    def test_debt_mismatch_does_not_invent_adjudication(self):
        for symbol in ('ADI', 'MUT'):
            with self.subTest(symbol=symbol):
                f = self.items[symbol]['fundamental']
                self.assertIsNone(f['net_debt_strict_mmad'])
                self.assertIsNone(f['net_debt_ebitda'])
                self.assertIn(f['debt_reconciliation']['status'],
                              ('unresolved', 'cash_unresolved'))
                self.assertIsNotNone(f['earnings_mmad'])

    def test_report_is_serializable_without_nan_and_input_not_modified(self):
        json.dumps(self.report, allow_nan=False)
        for symbol in ('ADI', 'MUT', 'TGCC'):
            original = copy.deepcopy(self.facts[symbol])
            calculate(self.fixture['records'][symbol], self.facts[symbol],
                      asof=self.asof)
            self.assertEqual(self.facts[symbol], original)


if __name__ == '__main__':
    unittest.main()
