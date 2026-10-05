import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from nour.engine import build_report
from nour.site import detail_page
from tools.import_jet_semester_oct05 import merge, reference, URL
from tools.import_remaining_semesters_oct04 import additions, merge as previous_import

ROOT = Path(__file__).resolve().parents[1]


class JetSemester(unittest.TestCase):
    def test_exact_reconciliation_and_same_semester_growth(self):
        r = reference()
        amounts = {k: Decimal(str(v)) for k, v in r['provenance']['reconciliation_mad'].items()}
        self.assertEqual(amounts['group_net'] + amounts['minority_net'], amounts['total_net'])
        self.assertEqual(amounts['result_before_tax'] + amounts['equity_accounted_income']
                         - amounts['goodwill_amortization'] - amounts['income_tax'], amounts['total_net'])
        self.assertEqual(Decimal(str(r['reported_net_millions'])) * 1000000, amounts['group_net'])
        self.assertEqual(Decimal(str(r['reported_net_previous_millions'])) * 1000000, amounts['previous_group_net'])
        growth = (amounts['group_net'] / amounts['previous_group_net'] - 1) * 100
        self.assertEqual(growth.quantize(Decimal('.01')), Decimal('-27.40'))
        self.assertEqual(r['reported_net_previous_period_end'], '2025-06-30')

    def test_targeted_import_replay_and_preservation(self):
        original = json.loads((ROOT / 'data/facts_reference.json').read_text())
        original['records']['JET']['latest_report'] = additions()['JET']['latest_report']
        before = copy.deepcopy(original)
        after = merge(original)
        self.assertEqual(original, before)
        self.assertEqual(merge(after), after)
        self.assertEqual(previous_import(after), after)
        for symbol, record in before['records'].items():
            if symbol != 'JET':
                self.assertEqual(after['records'][symbol], record)
        annual_before = {k: v for k, v in before['records']['JET'].items() if k != 'latest_report'}
        self.assertEqual({k: v for k, v in after['records']['JET'].items() if k != 'latest_report'}, annual_before)
        future = copy.deepcopy(after)
        future['records']['JET']['latest_report'] = {'period_end': '2027-06-30', 'keep': True}
        self.assertEqual(merge(future), future)
        unexpected = copy.deepcopy(before)
        unexpected['records']['JET']['latest_report']['document_url'] = 'https://example.org/other.pdf'
        with self.assertRaises(ValueError):
            merge(unexpected)

    def test_annual_ratios_scores_and_other_titles_are_unchanged(self):
        fixture = json.loads((ROOT / 'data/market_snapshot.json').read_text())
        facts = json.loads((ROOT / 'data/facts_reference.json').read_text())
        facts['records']['JET']['latest_report'] = additions()['JET']['latest_report']
        before = build_report(fixture, '2026-10-05', facts=facts['records'])
        after = build_report(fixture, '2026-10-05', facts=merge(facts)['records'])
        before_items = {r['symbol']: r for r in before['results']}
        after_items = {r['symbol']: r for r in after['results']}
        for symbol, item in before_items.items():
            updated = copy.deepcopy(after_items[symbol])
            if symbol == 'JET':
                self.assertEqual(updated['fundamental']['latest_report']['reported_net_millions'], 91.50954252)
                self.assertEqual(updated['fundamental']['eps_mad'], 73.39)
                updated['fundamental']['latest_report'] = item['fundamental']['latest_report']
            self.assertEqual(updated, item)

    def test_page_explains_group_result_comparison_and_source_reservations(self):
        fixture = json.loads((ROOT / 'data/market_snapshot.json').read_text())
        facts = json.loads((ROOT / 'data/facts_reference.json').read_text())
        report = build_report(fixture, '2026-10-05', facts=merge(facts)['records'])
        item = next(r for r in report['results'] if r['symbol'] == 'JET')
        record = fixture['records']['JET']
        page = detail_page(item, record, fixture, '', '')
        for expected in ('Résultat net part du groupe : 91,51', '126,04 millions', '-27,40 %',
                         '2025-06-30', URL, 'Réserve :', 'aucun doublement du semestre'):
            self.assertIn(expected, page)
        self.assertNotIn('Résultat inutilisable', page)


if __name__ == '__main__':
    unittest.main()
