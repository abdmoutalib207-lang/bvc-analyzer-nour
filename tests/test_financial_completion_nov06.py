"""Regression evidence for annual disclosures, scopes and unavailable ratios."""
import json
from pathlib import Path
import unittest

from nour.fundamentals import calculate
from nour.reported_facts import reported_facts

ROOT = Path(__file__).resolve().parents[1]


class FinancialCompletionNov06(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / 'data/facts_reference.json').read_text())['records']

    def test_addoha_exact_published_ca_and_group_profit_not_old_method_simulation(self):
        record = self.records['ADH']
        facts = record['faits']
        self.assertEqual(facts['chiffre_affaires']['valeur_au_rapport'], 2708923803)
        self.assertEqual(facts['chiffre_affaires_2024']['valeur_au_rapport'], 2594688796)
        result = calculate({'symbol': 'ADH', 'price': 30}, record, '2026-11-06')
        self.assertEqual(result['earnings_mmad'], 453.719263)
        self.assertEqual(result['eps_mad'], 1.13)
        self.assertEqual(result['roe_average_equity_pct'], 4.83)
        # Comparison requires a comparable method, independently of having amounts.
        self.assertIsNone(result['revenue_growth_pct'])
        self.assertIsNone(result['net_debt_ebitda'])
        rows = reported_facts(record, '2026-11-06')['records']
        self.assertTrue(any(r['label'] == 'Chiffre d’affaires' and r['value'] == 2708923803
                            and r['unit'] == 'MAD' and r['status'] == 'page_checked' for r in rows))

    def test_hps_and_cosumar_ca_are_not_total_operating_products(self):
        for symbol, amount, previous, growth in [('HPS', 1476.348064, 1204.347601, 22.58),
                                                  ('CSR', 10487.1, 10238.6, 2.43)]:
            record = self.records[symbol]
            self.assertEqual(record['faits']['chiffre_affaires']['valeur'], amount)
            self.assertEqual(record['faits']['chiffre_affaires_2024']['valeur'], previous)
            result = calculate({'symbol': symbol, 'price': 100}, record, '2026-11-06')
            self.assertEqual(result['revenue_growth_pct'], growth)
        self.assertEqual(self.records['HPS']['faits']['resultat_net_part_groupe']['valeur'], 105.777740)

    def test_existing_sector_disclosures_reused_without_changing_currency_or_debt(self):
        for symbol in ['AKD', 'ARD', 'LES', 'MUT', 'SNP', 'CTM', 'DSW', 'GAZ', 'SRM', 'IMI']:
            record = self.records[symbol]
            annual = dict(record['faits']['chiffre_affaires'])
            annual.pop('nour_origin')
            self.assertEqual(annual, record['sector_faits']['chiffre_affaires'])
        self.assertNotIn('chiffre_affaires', self.records['ENK']['faits'])
        for symbol, growth in [('AKD', 49.4), ('DSW', 9.01)]:
            result = calculate({'symbol': symbol, 'price': 100}, self.records[symbol], '2026-11-06')
            self.assertEqual(result['revenue_growth_pct'], growth)
            self.assertIsNone(result['net_debt_ebitda'])
        self.assertEqual(self.records['AKD']['sector_faits']['ebitda_publie']['valeur'], 1214)
        self.assertNotIn('excedent_brut_exploitation', self.records['AKD']['faits'])

    def test_taqa_issuer_pdf_keeps_its_identity_and_only_unresolved_multiple_is_blocked(self):
        record = self.records['TQA']
        fact = record['faits']['chiffre_affaires']
        self.assertEqual(fact['valeur'], 10637.640)
        self.assertEqual(fact['valeur_au_rapport'], 10637640)
        self.assertEqual(fact['unite_au_rapport'], 'KMAD')
        self.assertNotEqual(fact['url'], record['url'])
        self.assertIn('taqamorocco.ma', fact['url'])
        result = calculate({'symbol': 'TQA', 'price': 1000}, record, '2026-11-06')
        self.assertEqual(result['revenue_growth_pct'], -2.21)
        self.assertIsNotNone(result['earnings_mmad'])
        self.assertIsNotNone(result['roe_average_equity_pct'])
        self.assertIsNotNone(result['net_debt_strict_mmad'])
        self.assertIsNone(result['net_debt_ebitda'])


if __name__ == '__main__':
    unittest.main()
