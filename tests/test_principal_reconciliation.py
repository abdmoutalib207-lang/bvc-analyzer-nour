import unittest
from copy import deepcopy
from tools.reconcile_principal_facts import reconcile

SHA = 'a' * 40
URL = 'https://www.ammc.ma/sites/default/files/test.pdf'


class PrincipalReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.nour = {'origin': 'unchanged', 'records': {'ADH': {'exercice': 2025,
            'url': URL, 'reservations': ['keep'], 'provenance': {'commit': 'old'},
            'faits': {'chiffre_affaires': {'valeur': 2431.512, 'page': 2}}},
            'ADI': {'faits': {'other': {'valeur': 123}}}}}
        self.source = {'ADH': {'exercice': 2025, 'url': URL, 'faits': {
            'chiffre_affaires': {'valeur': 2432, 'page': 2},
            'nombre_actions': {'valeur': 100, 'page': 3, 'unite': 'actions',
                'validation_status': 'selected_pages_visually_checked', 'document_hash': 'sha256:' + 'b' * 64},
            'capitaux_propres_part_groupe_2024': {'valeur': 12.3, 'page': 4,
                'valeur_au_rapport': 12300, 'unite_au_rapport': 'KMAD'}}}}

    def test_default_report_is_immutable_and_preserves_precise_nour(self):
        before, source = deepcopy(self.nour), deepcopy(self.source)
        out, report = reconcile(self.source, self.nour, SHA, ['ADH'])
        self.assertEqual(out, before)
        self.assertEqual(self.nour, before)
        self.assertEqual(self.source, source)
        self.assertEqual(len(report['candidates']), 2)
        self.assertEqual(report['different_values'][0]['nour_value'], 2431.512)

    def test_apply_preserves_old_record_and_units_without_certification(self):
        out, _ = reconcile(self.source, self.nour, SHA, ['ADH'], True)
        original = deepcopy(out['records']['ADH'])
        for key in ('nombre_actions', 'capitaux_propres_part_groupe_2024'):
            original['faits'].pop(key)
        self.assertEqual(original, self.nour['records']['ADH'])
        self.assertEqual(out['records']['ADI'], self.nour['records']['ADI'])
        shares = out['records']['ADH']['faits']['nombre_actions']
        self.assertEqual(shares['unite'], 'actions')
        self.assertNotIn('document_hash', shares)
        self.assertEqual(shares['validation_status'], 'referenced_import_not_independent_audit')
        self.assertEqual(shares['import_provenance']['commit'], SHA)
        equity = out['records']['ADH']['faits']['capitaux_propres_part_groupe_2024']
        self.assertEqual(equity['unite_au_rapport'], 'KMAD')
        self.assertEqual(equity['valeur_au_rapport'], 12300)

    def test_rejects_bad_period_document_scope_and_values(self):
        facts = self.source['ADH']['faits']
        facts.clear()
        facts.update({'resultat_net_part_groupe': {'valeur': 5, 'page': 2, 'base': 'SOCIAL'},
            'x': {'valeur': float('nan'), 'page': 2}, 'y': {'valeur': 4, 'page': True},
            'z': {'valeur': 4, 'page': 2, 'url': 'https://elsewhere.test/x'},
            'later': {'valeur': 4, 'page': 2, 'period_end': '2026-06-30'}})
        out, report = reconcile(self.source, self.nour, SHA, ['ADH'], True)
        self.assertEqual(out, self.nour)
        self.assertEqual(len(report['candidates']), 0)
        self.source['ADH']['url'] = 'different'
        self.assertEqual(reconcile(self.source, self.nour, SHA)[1]['rejected'][0]['reason'], 'period_or_document_mismatch')
        with self.assertRaises(ValueError):
            reconcile(self.source, self.nour, 'main')
