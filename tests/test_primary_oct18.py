"""Primary evidence, scope conflicts and real valuation consequences of October 18."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from nour.fundamentals import calculate
from nour.sector_audit import audit_sector_report
from tools.import_primary_oct18 import merge, review_data, verify_pdfs

ROOT = Path(__file__).resolve().parents[1]


class PrimaryOctober18Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT/'data/facts_reference.json').read_text())
        cls.reviews = review_data()['records']

    def test_replay_is_idempotent_and_preserves_other_issuers_and_every_semester(self):
        before = deepcopy(self.document)
        after = merge(before)
        self.assertEqual(before, self.document)
        self.assertEqual(merge(after), after)
        for s, r in before['records'].items():
            self.assertEqual(r.get('latest_report'), after['records'][s].get('latest_report'))
            if s not in self.reviews:
                self.assertEqual(r, after['records'][s])

    def test_source_revision_and_newer_exercise_are_not_overwritten(self):
        for s in self.reviews:
            d = deepcopy(self.document)
            d['records'][s]['url'] = 'https://example.org/replaced.pdf'
            with self.assertRaises(ValueError):
                merge(d)
            d = deepcopy(self.document)
            d['records'][s]['financial_review']['document_hash'] = 'sha256:'+'0'*64
            with self.assertRaises(ValueError):
                merge(d)
            d = deepcopy(self.document)
            d['records'][s]['exercice'] = 2026
            self.assertEqual(merge(d)['records'][s], d['records'][s])
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'TGCC.pdf').write_bytes(b'wrong report')
            with self.assertRaises(ValueError):
                verify_pdfs(directory)

    def test_new_bpa_uses_group_or_social_result_and_unrounded_per(self):
        for symbol, net, shares in [('TGCC','952.053',34674332), ('AFM','72.655851',1000000),
                                   ('AGM','71.02753751',200000), ('ATL','467.639',60283595),
                                   ('WAF','1026.036',3500000)]:
            with self.subTest(symbol=symbol):
                f = calculate({'symbol':symbol,'price':123.45}, self.document['records'][symbol], asof='2026-10-18')
                eps = Decimal(net)*1000000/Decimal(shares)
                self.assertEqual(f['eps_mad'], float(round(eps,2)))
                self.assertEqual(f['pe'], float(round(Decimal('123.45')/eps,2)))
                self.assertIn('indicatif', f['eps_denominator'])
                self.assertFalse(f['financial_audit']['documents_certified'])
                key = 'resultat_net_social' if symbol == 'AGM' else 'resultat_net_part_groupe'
                self.assertEqual(f['evidence'][key]['document_hash'], self.reviews[symbol]['document_hash'])

    def test_conflicting_published_bpa_only_withholds_bpa_and_per(self):
        for s, net, equity in [('CMGP',244.010766,2788.340389), ('SGTM',1341.942,3550.399), ('CFGB',370.445,2065.577)]:
            with self.subTest(symbol=s):
                facts = self.document['records'][s]
                f = calculate({'symbol':s,'price':100},facts,asof='2026-10-18')
                self.assertIsNone(f['eps_mad']); self.assertIsNone(f['pe'])
                self.assertEqual(f['earnings_mmad'],net)
                self.assertEqual(f['roe_pct'],round(net/equity*100,2))
                self.assertIsNotNone(f['pb'])
                self.assertIn('documentary_reconciliation_pending', f['metric_availability']['eps_mad']['reason_codes'])
                actions = audit_sector_report({'results':[{'symbol':s,'fundamental':f}]})['review_queue']
                self.assertTrue(any(a['code']=='documentary_reconciliation_pending' and a['source_pages_to_check'] for a in actions))
                resolved = deepcopy(facts)
                resolved['calculation_reservations'][0]['status'] = 'resolved'
                self.assertIsNotNone(calculate({'price':100},resolved,asof='2026-10-18')['eps_mad'])

    def test_malformed_restriction_fails_closed_and_does_not_mutate_facts(self):
        f = deepcopy(self.document['records']['CMGP'])
        before = deepcopy(f)
        calculate({'price':100},f,asof='2026-10-18')
        self.assertEqual(f,before)
        for bad in [None,{}, {'status':'unresolved','metrics':['typo'],'fields':['resultat_net_part_groupe'],'detail':'Review'}]:
            f['calculation_reservations']=[bad]
            if bad == {}:continue  # No unresolved status is not an active restriction.
            with self.assertRaises(ValueError):
                calculate({'price':100},f,asof='2026-10-18')

    def test_cmgp_never_replaces_group_profit_by_note_total_and_afma_keeps_ifrs16(self):
        c = self.document['records']['CMGP']['faits']
        self.assertAlmostEqual(c['resultat_net_consolide']['valeur']-c['resultat_net_part_groupe']['valeur'],8.744177)
        f = calculate({'price':100},self.document['records']['AFM'],asof='2026-10-18')
        self.assertEqual(f['earnings_mmad'],72.655851)
        self.assertNotEqual(f['earnings_mmad'],70.204)
        self.assertTrue(any('IFRS 16' in s for s in f['warnings']))
        self.assertEqual(self.document['records']['ATL']['faits']['nombre_actions_au_rapport']['valeur'],60283595)
        self.assertEqual(self.document['records']['CFGB']['faits']['nombre_actions_au_rapport']['valeur'],35007960)


if __name__ == '__main__':
    unittest.main()
