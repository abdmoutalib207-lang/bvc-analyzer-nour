import copy
import json
from pathlib import Path
import tempfile
import unittest

from nour.fundamentals import calculate
from tools.import_tma_primary_oct16 import HASH, URL, S1_HASH, S1_URL, merge, verify_pdf


class TmaPrimaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((Path(__file__).resolve().parents[1] / 'data/facts_reference.json').read_text())

    def test_replay_idempotent_preserves_semesters_and_other_issuers(self):
        before = copy.deepcopy(self.document)
        after = merge(before)
        self.assertEqual(before, self.document)
        self.assertEqual(merge(after), after)
        for symbol, record in before['records'].items():
            self.assertEqual(record.get('latest_report'), after['records'][symbol].get('latest_report'))
            if symbol != 'TMA':
                self.assertEqual(record, after['records'][symbol])

    def test_stale_annual_upgraded_without_retaining_false_absence_claim(self):
        old = copy.deepcopy(self.document)
        old['records']['TMA'] = {'exercice': 2024, 'url': 'https://www.ammc.ma/sites/default/files/Total_RFA_2024.pdf',
                                'faits': {'old': {'note': 'AMMC ne sert pas de rapport 2025'}},
                                'latest_report': {'period_end': '2026-06-30', 'keep': True}}
        record = merge(old)['records']['TMA']
        self.assertEqual(record['exercice'], 2025)
        self.assertEqual(record['latest_report'], old['records']['TMA']['latest_report'])
        self.assertNotIn('old', record['faits'])
        self.assertIn('old', record['annual_reference_prior_oct16']['faits'])

    def test_future_period_source_or_hash_conflict_not_silently_overwritten(self):
        future = copy.deepcopy(self.document)
        future['records']['TMA']['exercice'] = 2026
        self.assertEqual(merge(future), future)
        changed = copy.deepcopy(self.document)
        changed['records']['TMA']['url'] = 'https://example.org/other.pdf'
        with self.assertRaises(ValueError):
            merge(changed)
        changed = merge(self.document)
        changed['records']['TMA']['faits']['resultat_net_part_groupe']['document_hash'] = 'sha256:' + '0' * 64
        with self.assertRaises(ValueError):
            merge(changed)
        changed = merge(self.document)
        changed['records']['TMA']['complementary_reference_verified']['document_hash'] = 'sha256:' + '1' * 64
        with self.assertRaises(ValueError):
            merge(changed)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changed.pdf'
            path.write_bytes(b'changed source')
            with self.assertRaises(ValueError):
                verify_pdf(path)

    def test_annual_ratios_use_primary_group_units_and_published_closing_shares(self):
        record = merge(self.document)['records']['TMA']
        result = calculate({'price': 1500}, record)
        self.assertEqual(result['exercise'], 2025)
        self.assertEqual(result['eps_mad'], round(851083000 / 8960000, 2))
        self.assertEqual(result['pe'], round(1500 / (851083000 / 8960000), 2))
        self.assertEqual(result['book_value_per_share_mad'], round(1984665000 / 8960000, 2))
        self.assertEqual(result['pb'], round(1500 / (1984665000 / 8960000), 2))
        self.assertEqual(result['roe_pct'], round(851.083 / 1984.665 * 100, 2))
        self.assertEqual(result['roe_average_equity_pct'], round(851.083 / ((1984.665 + 2745.769) / 2) * 100, 2))
        self.assertEqual(result['revenue_growth_pct'], round((15126.704 / 16751.842 - 1) * 100, 2))
        self.assertNotEqual(result['eps_mad'], round(284.955 * 2e6 / 8960000, 2))
        for key in ('resultat_net_part_groupe', 'capitaux_propres_part_groupe', 'nombre_actions'):
            evidence = result['evidence'][key]
            self.assertEqual(evidence['document_url'], URL)
            self.assertEqual(evidence['document_hash'], HASH)
            self.assertEqual(evidence['validation_status'], 'selected_pages_visually_checked')
        self.assertEqual(result['evidence']['nombre_actions']['page'], 3)
        self.assertIn('indicatif', result['eps_denominator'])

    def test_latest_debt_separate_no_lease_scope_assumption_or_semester_annualization(self):
        record = merge(self.document)['records']['TMA']
        result = calculate({'price': 1500}, record)
        reference = record['complementary_reference_verified']
        self.assertEqual(reference['document_url'], S1_URL)
        self.assertEqual(reference['document_hash'], S1_HASH)
        self.assertEqual(reference['period_end'], '2026-06-30')
        self.assertAlmostEqual(reference['debt_components_mmad']['noncurrent'] + reference['debt_components_mmad']['current'] - reference['debt_components_mmad']['cash'], 326.343)
        self.assertAlmostEqual(reference['annual_comparative_net_debt_mmad'], -288.580)
        self.assertIsNone(result['net_debt_strict_mmad'])
        self.assertIsNone(result['net_debt_ebitda'])
        self.assertEqual(result['latest_report'], self.document['records']['TMA']['latest_report'])
        self.assertTrue(any('326,343' in warning and 'locations' in warning for warning in result['warnings']))
        self.assertNotIn('dividende_par_action', record['faits'])  # AGO project is not proof of voted dividend.


if __name__ == '__main__':
    unittest.main()
