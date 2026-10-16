import copy
import json
from pathlib import Path
import unittest
import tempfile

from nour.fundamentals import calculate
from tools.import_rds_primary_oct16 import merge, verify_pdf, URL, HASH


class RdsPrimaryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((Path(__file__).resolve().parents[1] / 'data/facts_reference.json').read_text())

    def test_replay_preserves_all_semesters_other_issuers_and_is_idempotent(self):
        before = copy.deepcopy(self.document)
        after = merge(before)
        self.assertEqual(before, self.document)
        self.assertEqual(merge(after), after)
        for s, r in before['records'].items():
            self.assertEqual(r.get('latest_report'), after['records'][s].get('latest_report'))
            if s != 'RDS':
                self.assertEqual(r, after['records'][s])

    def test_new_exercise_not_overwritten_and_other_source_refused(self):
        future = copy.deepcopy(self.document)
        future['records']['RDS']['exercice'] = 2026
        self.assertEqual(merge(future), future)
        wrong = copy.deepcopy(self.document)
        wrong['records']['RDS']['url'] = 'https://example.org/other.pdf'
        with self.assertRaises(ValueError):
            merge(wrong)

    def test_changed_document_never_silently_replaces_primary_proof(self):
        changed = copy.deepcopy(self.document)
        changed['records']['RDS']['financial_review'] = {'document_hash': 'sha256:' + '0' * 64}
        with self.assertRaises(ValueError):
            merge(changed)
        changed = copy.deepcopy(self.document)
        changed['records']['RDS']['faits']['resultat_net_part_groupe'] = {
            'valeur': 7, 'document_hash': 'sha256:' + '1' * 64}
        with self.assertRaises(ValueError):
            merge(changed)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wrong.pdf'
            path.write_bytes(b'not the reviewed annual report')
            with self.assertRaises(ValueError):
                verify_pdf(path)

    def test_primary_scope_units_and_denominator_propagate_into_real_ratios(self):
        f = merge(self.document)['records']['RDS']
        # Independently published facts: result total + minority loss = group.
        self.assertAlmostEqual(4.491 - (-.003), f['faits']['resultat_net_part_groupe']['valeur'])
        self.assertEqual(f['faits']['nombre_actions']['valeur'], 26208850)
        r = calculate({'price': 159.6}, f)
        self.assertEqual(r['eps_mad'], round(4494000 / 26208850, 2))
        self.assertEqual(r['pe'], round(159.6 / (4494000 / 26208850), 2))
        self.assertEqual(r['roe_pct'], round(4.494 / 3739.480 * 100, 2))
        self.assertEqual(r['book_value_per_share_mad'], round(3739480000 / 26208850, 2))
        self.assertEqual(r['revenue_growth_pct'], round((468.513 / 233.682 - 1) * 100, 2))
        self.assertEqual(r['debt_reconciliation']['status'], 'not_cross_checked')
        self.assertIsNone(r['net_debt_ebitda'])
        for key in ('resultat_net_part_groupe', 'capitaux_propres_part_groupe', 'nombre_actions'):
            e = r['evidence'][key]
            self.assertEqual(e['document_url'], URL)
            self.assertEqual(e['document_hash'], HASH)
            self.assertEqual(e['validation_status'], 'selected_pages_visually_checked')
        self.assertEqual(r['latest_report'], self.document['records']['RDS']['latest_report'])
        self.assertEqual(r['validation_status'], 'referenced_import')


if __name__ == '__main__':
    unittest.main()
