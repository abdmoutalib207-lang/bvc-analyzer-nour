import unittest
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from tools.reconcile_principal_facts import reconcile

SHA = 'a' * 40
URL = 'https://www.ammc.ma/sites/default/files/test.pdf'


class PrincipalReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.nour = {'origin': 'unchanged', 'records': {'ADH': {'exercice': 2025,
            'accounting_basis': 'consolidé IFRS',
            'url': URL, 'reservations': ['keep'], 'provenance': {'commit': 'old'},
            'faits': {'chiffre_affaires': {'valeur': 2431.512, 'page': 2}}},
            'ADI': {'faits': {'other': {'valeur': 123}}}}}
        self.source = {'ADH': {'exercice': 2025, 'url': URL, 'faits': {
            'chiffre_affaires': {'valeur': 2432, 'page': 2},
            'nombre_actions': {'valeur': 100, 'page': 3, 'unite': 'actions',
                'period_end': '2025-12-31',
                'validation_status': 'selected_pages_visually_checked', 'document_hash': 'sha256:' + 'b' * 64},
            'capitaux_propres_part_groupe_2024': {'valeur': 12.3, 'page': 4,
                'base': 'consolidé IFRS', 'period_end': '2024-12-31',
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

    def test_comparative_cannot_use_current_column_date(self):
        fact = self.source['ADH']['faits']['capitaux_propres_part_groupe_2024']
        fact['period_end'] = '2025-12-31'
        out, report = reconcile(self.source, self.nour, SHA, apply=True)
        self.assertNotIn('capitaux_propres_part_groupe_2024', out['records']['ADH']['faits'])
        self.assertIn('different_fact_period', [r['reason'] for r in report['rejected']])

    def test_missing_scope_or_unit_and_wrong_scale_are_not_promoted(self):
        template = {'valeur': 12.3, 'page': 4, 'base': 'consolidé IFRS',
                    'period_end': '2025-12-31', 'unite': 'MMAD'}
        cases = [({**template, 'base': ''}, 'missing_accounting_scope'),
                 ({k: v for k, v in template.items() if k != 'unite'}, 'missing_numeric_unit'),
                 ({**template, 'unite': 'MAD'}, 'invalid_canonical_unit'),
                 ({**template, 'valeur_au_rapport': 12300, 'unite_au_rapport': 'MAD'}, 'inconsistent_unit_conversion'),
                 ({**template, 'devise': 'EUR'}, 'different_currency'),
                 ({**template, 'period_end': None}, 'missing_fact_period')]
        for fact, reason in cases:
            with self.subTest(reason=reason):
                source = deepcopy(self.source)
                source['ADH']['faits'] = {'chiffre_affaires_2025': fact}
                out, report = reconcile(source, self.nour, SHA, apply=True)
                self.assertEqual(out, self.nour)
                self.assertEqual(report['rejected'][0]['reason'], reason)

    def test_explicit_report_column_and_raw_scale_allow_legacy_money(self):
        self.source['ADH']['faits'] = {'chiffre_affaires_2024': {
            'valeur': 12.3, 'page': 4, 'base': 'consolidé IFRS',
            'colonne_exercice_precedent': 2,
            'valeur_au_rapport': 12300, 'unite_au_rapport': 'KMAD'}}
        out, report = reconcile(self.source, self.nour, SHA, apply=True)
        fact = out['records']['ADH']['faits']['chiffre_affaires_2024']
        self.assertEqual(fact['unite'], 'MMAD')
        self.assertEqual(fact['period_end'], '2024-12-31')
        self.assertFalse(report['rejected'])

    def test_named_social_fact_is_not_imported_as_consolidated_fallback(self):
        self.source['ADH']['faits'] = {'resultat_net_social': {
            'valeur': 12.3, 'page': 4, 'base': 'social',
            'period_end': '2025-12-31', 'unite': 'MMAD'}}
        out, report = reconcile(self.source, self.nour, SHA, apply=True)
        self.assertEqual(out, self.nour)
        self.assertEqual(report['rejected'][0]['reason'], 'different_accounting_scope')
        self.nour['records']['ADH']['accounting_basis'] = 'social (normes marocaines)'
        out, report = reconcile(self.source, self.nour, SHA, apply=True)
        self.assertEqual(out['records']['ADH']['faits']['resultat_net_social']['base'], 'social')
        self.assertFalse(report['rejected'])
        self.source['ADH']['faits'] = {'resultat_net_part_groupe': {
            'valeur': 12.3, 'page': 4, 'base': 'consolidé (normes marocaines)',
            'period_end': '2025-12-31', 'unite': 'MMAD'}}
        out, report = reconcile(self.source, self.nour, SHA, apply=True)
        self.assertEqual(out, self.nour)
        self.assertEqual(report['rejected'][0]['reason'], 'different_accounting_scope')

    def test_cli_apply_writes_readable_json_and_preserves_source(self):
        with TemporaryDirectory() as directory:
            source, facts = Path(directory) / 'source.json', Path(directory) / 'facts.json'
            source.write_text(json.dumps(self.source), encoding='utf-8')
            facts.write_text(json.dumps(self.nour), encoding='utf-8')
            original_source = source.read_bytes()
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/reconcile_principal_facts.py'),
                       '--source', str(source), '--facts', str(facts), '--source-commit', SHA]
            dry = subprocess.run(command, capture_output=True, text=True, check=True)
            self.assertFalse(json.loads(dry.stdout)['applied'])
            self.assertEqual(json.loads(facts.read_text(encoding='utf-8')), self.nour)
            applied = subprocess.run(command + ['--apply'], capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(applied.stdout)['applied'])
            self.assertEqual(source.read_bytes(), original_source)
            result = json.loads(facts.read_text(encoding='utf-8'))
            self.assertEqual(result['records']['ADH']['faits']['nombre_actions']['valeur'], 100)

    def test_same_scope_different_accounting_standard_is_rejected(self):
        self.source['ADH']['faits'] = {'chiffre_affaires_2025': {
            'valeur': 12.3, 'page': 4, 'base': 'consolidé (normes marocaines, avis CNC n°5)',
            'period_end': '2025-12-31', 'unite': 'MMAD'}}
        for target, source in [('consolidé IFRS', 'consolidé (normes marocaines)'),
                               ('Consolidé CGNC', 'consolidé IFRS'),
                               ('consolidé normes nationales', 'Consolidé IAS/IFRS')]:
            with self.subTest(target=target, source=source):
                self.nour['records']['ADH']['accounting_basis'] = target
                self.source['ADH']['faits']['chiffre_affaires_2025']['base'] = source
                out, report = reconcile(self.source, self.nour, SHA, apply=True)
                self.assertEqual(out, self.nour)
                self.assertEqual(report['rejected'][0]['reason'], 'different_accounting_standard')
        self.nour['records']['ADH']['accounting_basis'] = 'consolidé normes marocaines'
        self.source['ADH']['faits']['chiffre_affaires_2025']['base'] = 'Consolidé CGNC'
        out, report = reconcile(self.source, self.nour, SHA, apply=True)
        self.assertEqual(out['records']['ADH']['faits']['chiffre_affaires_2025']['base'], 'Consolidé CGNC')
        self.assertFalse(report['rejected'])
