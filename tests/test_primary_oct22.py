"""Annual primary results: minority interests, social scope and replay safety."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from nour.fundamentals import calculate
from tools.import_primary_oct22 import merge, review_data, verify_pdfs

ROOT = Path(__file__).resolve().parents[1]


class PrimaryOctober22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT/'data/facts_reference.json').read_text())
        cls.reviews = review_data()['records']

    def test_replay_preserves_input_other_issuers_and_all_semesters(self):
        original = deepcopy(self.document)
        after = merge(original)
        self.assertEqual(original, self.document)
        self.assertEqual(merge(after), after)
        for symbol, record in original['records'].items():
            self.assertEqual(record.get('latest_report'), after['records'][symbol].get('latest_report'))
            if symbol not in self.reviews:
                self.assertEqual(record, after['records'][symbol])

    def test_revised_source_hash_or_newer_exercise_is_not_overwritten(self):
        for symbol in self.reviews:
            document = deepcopy(self.document)
            document['records'][symbol]['url'] = 'https://example.org/revision.pdf'
            with self.assertRaises(ValueError):
                merge(document)
            document = deepcopy(self.document)
            document['records'][symbol]['financial_review']['document_hash'] = 'sha256:'+'0'*64
            with self.assertRaises(ValueError):
                merge(document)
            document = deepcopy(self.document)
            document['records'][symbol]['faits'][next(iter(self.reviews[symbol]['facts']))]['document_hash'] = 'sha256:'+'0'*64
            with self.assertRaises(ValueError):
                merge(document)
            document = deepcopy(self.document)
            document['records'][symbol]['exercice'] = 2026
            self.assertEqual(merge(document)['records'][symbol], document['records'][symbol])
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'AKD.pdf').write_bytes(b'not the reviewed PDF')
            with self.assertRaises(ValueError):
                verify_pdfs(directory)

    def test_explicit_group_profit_and_exact_per_use_full_precision(self):
        cases = [('AKD','443.680156',14159207), ('ARD','534.413',12568130),
                 ('CTM','56.204',1225978), ('DSW','85.45793176',1885762),
                 ('GAZ','750.5',3437500), ('IMI','41.486',9007000),
                 ('LES','8',27631510)]
        for symbol, net, shares in cases:
            with self.subTest(symbol=symbol):
                out = calculate({'price':123.45}, self.document['records'][symbol], asof='2026-10-22')
                eps = Decimal(net)*1000000/Decimal(shares)
                self.assertEqual(out['earnings_mmad'], float(net))
                self.assertEqual(out['eps_mad'], float(round(eps, 2)))
                self.assertEqual(out['pe'], float(round(Decimal('123.45')/eps, 2)))
                self.assertFalse(out['financial_audit']['documents_certified'])
                self.assertEqual(out['evidence']['resultat_net_part_groupe']['document_hash'], self.reviews[symbol]['document_hash'])
        self.assertEqual(self.document['records']['CTM']['faits']['resultat_net_consolide']['valeur'], 16.083)
        self.assertEqual(self.document['records']['LES']['faits']['resultat_net_consolide']['valeur'], 5)

    def test_social_keys_replace_misclassified_total_without_erasing_history(self):
        for symbol, net in [('SRM',12.06621642), ('STR',0.47601982)]:
            facts = self.document['records'][symbol]
            out = calculate({'price':100}, facts, asof='2026-10-22')
            self.assertNotIn('resultat_net_consolide', facts['faits'])
            self.assertIsNotNone(facts['reconciliation_prior_oct22']['resultat_net_consolide'])
            self.assertEqual(out['earnings_mmad'], net)
            self.assertIn('resultat_net_social', out['evidence'])
            self.assertNotIn('resultat_net_part_groupe', out['evidence'])

    def test_loss_negative_equity_and_existing_documentary_conflicts_stay_blocked(self):
        snep = calculate({'price':100}, self.document['records']['SNP'], asof='2026-10-22')
        self.assertEqual(snep['eps_mad'], -77.16)
        self.assertIsNone(snep['pe'])
        self.assertLess(snep['roe_pct'], 0)
        stroc = calculate({'price':100}, self.document['records']['STR'], asof='2026-10-22')
        self.assertIsNotNone(stroc['eps_mad'])
        self.assertIsNone(stroc['pb'])
        self.assertIsNone(stroc['roe_pct'])
        self.assertTrue(any('réserve' in w for w in stroc['warnings']))
        for symbol in ('CFGB','CMGP','SGTM'):
            out = calculate({'price':100}, self.document['records'][symbol], asof='2026-10-22')
            self.assertIsNone(out['eps_mad'])
            self.assertIsNone(out['pe'])
        for symbol in ('ADI','MUT'):
            out = calculate({'price':100}, self.document['records'][symbol], asof='2026-10-22')
            self.assertIsNone(out['net_debt_strict_mmad'])
            self.assertIsNone(out['net_debt_ebitda'])

    def test_conflicting_opening_equity_is_not_used_and_old_total_guard_survives(self):
        out = calculate({'price':100}, self.document['records']['IMI'], asof='2026-10-22')
        self.assertIsNone(out['roe_average_equity_pct'])
        for symbol in ('AKD','CTM','LES'):
            facts = deepcopy(self.document['records'][symbol])
            facts['faits'].pop('resultat_net_part_groupe')
            out = calculate({'price':100}, facts, asof='2026-10-22')
            self.assertIsNone(out['earnings_mmad'])
            self.assertIsNone(out['pe'])
            self.assertIn('group_earnings_missing_total_not_substituted',
                          [x['code'] for x in out['financial_audit']['checks']])


if __name__ == '__main__':
    unittest.main()
