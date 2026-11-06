import copy
import json
from pathlib import Path
import unittest

from nour.bi_view import financial_dashboard, semester_chart
from nour.fundamentals import calculate


class BiViewTests(unittest.TestCase):
    def annual_revenue_item(self):
        return {'fundamental': {'exercise': 2025, 'period_end': '2025-12-31',
            'currency': 'MAD', 'accounting_basis': 'Consolidé IFRS',
            'evidence': {'chiffre_affaires': {'value': 2431.512, 'unit': 'MMAD',
                'period_end': '2025-12-31', 'currency': 'MAD', 'accounting_basis': 'Consolidé IFRS',
                'document_url': 'https://www.ammc.ma/annual.pdf', 'page': 54}}}}

    def test_annual_revenue_amount_is_visible_when_growth_is_not_comparable(self):
        item = self.annual_revenue_item()
        item['fundamental'].update(revenue_growth_pct=None, metric_availability={
            'revenue_growth_pct': {'status': 'blocked', 'reason_codes': ['comparability_unresolved']}})
        before = copy.deepcopy(item)
        page = financial_dashboard(item)
        self.assertIn('Chiffre d’affaires annuel', page)
        self.assertIn('data-bi-metric="annual_revenue_mmad"', page)
        self.assertIn('>2 431,51<', page)
        self.assertIn('MMAD', page)
        self.assertIn('2025-12-31', page)
        self.assertIn('annual.pdf#page=54', page)
        self.assertIn('comparability_unresolved', page)
        self.assertIn('1 / 9 indicateurs affichables', page)
        self.assertEqual(item, before)

    def test_annual_revenue_requires_its_own_compatible_evidence(self):
        for field, invalid in [('value', None), ('value', True), ('value', float('nan')),
                               ('unit', None), ('unit', 'KMAD'), ('currency', 'EUR'),
                               ('period_end', None), ('period_end', '2025-06-30'),
                               ('accounting_basis', 'Social'), ('accounting_basis', None),
                               ('page', 0), ('page', True), ('document_url', 'javascript:alert(1)')]:
            item = self.annual_revenue_item()
            item['fundamental']['evidence']['chiffre_affaires'][field] = invalid
            page = financial_dashboard(item)
            self.assertNotIn('data-bi-metric="annual_revenue_mmad"', page, (field, invalid))
        for field, invalid in [('currency', 'EUR'), ('period_end', None), ('accounting_basis', None)]:
            item = self.annual_revenue_item()
            item['fundamental'][field] = invalid
            self.assertNotIn('data-bi-metric="annual_revenue_mmad"', financial_dashboard(item))

    def test_annual_revenue_never_comes_from_semester_pnb_or_other_products(self):
        item = self.annual_revenue_item()
        evidence = item['fundamental']['evidence']
        fact = evidence.pop('chiffre_affaires')
        evidence['produits_exploitation'] = fact
        item['fundamental'].update(pnb_mmad=2431.512,
            latest_report={'revenue_millions': 2431.512, 'period_end': '2026-06-30'})
        self.assertNotIn('data-bi-metric="annual_revenue_mmad"', financial_dashboard(item))
        for value in (0, -12.5):
            item = self.annual_revenue_item()
            item['fundamental']['evidence']['chiffre_affaires']['value'] = value
            self.assertIn('data-bi-metric="annual_revenue_mmad"', financial_dashboard(item))

    def test_annual_revenue_basis_normalizes_date_suffixes_only(self):
        item = self.annual_revenue_item()
        item['fundamental']['accounting_basis'] = 'consolidé IFRS, 31/12/2025'
        self.assertIn('data-bi-metric="annual_revenue_mmad"', financial_dashboard(item))
        item['fundamental']['accounting_basis'] = 'consolidé normes marocaines, 31/12/2025'
        self.assertNotIn('data-bi-metric="annual_revenue_mmad"', financial_dashboard(item))

    def test_current_adh_annual_revenue_survives_its_growth_comparability_block(self):
        facts = json.loads((Path(__file__).resolve().parents[1] / 'data/facts_reference.json').read_text())['records']['ADH']
        result = calculate({'symbol': 'ADH', 'price': None}, facts, '2026-11-06')
        self.assertIsNone(result['revenue_growth_pct'])
        self.assertEqual(result['metric_availability']['revenue_growth_pct']['status'], 'blocked')
        page = financial_dashboard({'fundamental': result})
        self.assertIn('data-bi-metric="annual_revenue_mmad"', page)
        self.assertIn('>2 708,92<', page)
        self.assertIn('Addoha_RFA_2025.pdf#page=54', page)

    def test_view_preserves_numbers_and_unresolved_debt_without_recomputing(self):
        item = {'asof': '2026-10-15', 'fundamental': {'exercise': 2025,
            'eps_mad': .17, 'pe': 943.03, 'roe_pct': 0, 'net_debt_ebitda': None,
            'debt_reconciliation': {'status': 'unresolved'},
            'document_url': 'https://www.ammc.ma/document.pdf'}}
        before = copy.deepcopy(item)
        page = financial_dashboard(item)
        self.assertEqual(item, before)
        self.assertIn('943,03', page)
        self.assertIn('BPA non arrondi', page)
        self.assertIn('Suspendu : dette à rapprocher', page)
        self.assertIn('0,00', page)
        self.assertIn('3 / 8 indicateurs affichables', page)

    def test_loss_is_explained_and_unsafe_source_is_not_a_link(self):
        page = financial_dashboard({'fundamental': {'earnings_mmad': -10,
            'document_url': 'javascript:alert(1)', 'roe_method': '<script>bad</script>'}})
        self.assertIn('Une perte publiée n’est pas une donnée manquante', page)
        self.assertNotIn('href="javascript:', page)
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_missing_and_non_finite_values_are_not_displayed_as_zero(self):
        page = financial_dashboard({'fundamental': {'pe': float('nan'), 'roe_pct': True}})
        self.assertIn('0 / 8 indicateurs affichables', page)
        self.assertNotIn('>0,00<', page)
        self.assertNotIn('>nan<', page)
        self.assertIn('Indisponible', page)

    def test_bank_activity_is_labelled_pnb_separately(self):
        page = financial_dashboard({'fundamental': {'pnb_mmad': 2000, 'pnb_growth_pct': 4}})
        self.assertIn('Croissance du PNB', page)
        self.assertNotIn('Croissance du CA', page)
        self.assertIn('Produit net bancaire', page)

    def test_financial_sector_missing_pnb_does_not_become_industrial_ca(self):
        item = {'sector_guidance': {'family': 'Banque'},
                'fundamental': {'pnb_mmad': None, 'pnb_growth_pct': None,
                                'revenue_growth_pct': 12, 'eps_mad': 3.4}}
        page = financial_dashboard(item)
        self.assertIn('Croissance du PNB', page)
        self.assertIn('Produit net bancaire', page)
        self.assertNotIn('Croissance du CA', page)
        self.assertNotIn('>12,00<', page)
        self.assertIn('1 / 9 indicateurs affichables', page)
        # Missing PNB does not suppress independently available EPS.
        self.assertIn('>3,40<', page)
        for family in ('Finance - crédit-bail', 'Finance - crédit à la consommation'):
            self.assertIn('Croissance du PNB',
                          financial_dashboard({'sector_guidance': {'family': family},
                                               'fundamental': {}}))

    def test_unreasonably_large_integer_is_not_rendered_as_a_valid_number(self):
        page = financial_dashboard({'fundamental': {'pe': 10 ** 1000}})
        self.assertIn('0 / 8 indicateurs affichables', page)

    def test_independent_annual_net_is_visible_and_blocked_status_is_explicit(self):
        item = {'fundamental': {'exercise': 2025, 'earnings_mmad': -12.5,
                'evidence': {'resultat_net_part_groupe': {'page': 18}},
                'metric_availability': {
                    'earnings_mmad': {'status': 'available', 'reason_codes': []},
                    'eps_mad': {'status': 'blocked', 'reason_codes': ['fact_unit_mismatch']}}}}
        page = financial_dashboard(item)
        self.assertIn('Résultat net part du groupe', page)
        self.assertIn('>-12,50<', page)
        self.assertIn('Bloqué par contrôle', page)
        self.assertIn('fact_unit_mismatch', page)
        self.assertIn('1 / 8 indicateurs affichables', page)
        self.assertNotIn('Résultat net consolidé total', page)

    def test_graph_requires_explicit_same_half_year_group_comparison(self):
        data = dict(period_end='2026-06-30', reported_net_previous_period_end='2025-06-30',
                    currency='MAD', accounting_basis='Consolidé IFRS', reported_net_label='Résultat part du groupe',
                    reported_net_millions=-12, reported_net_previous_millions=15)
        chart = semester_chart(data)
        self.assertIn('-12,00', chart)
        self.assertIn('15,00', chart)
        self.assertIn('class="loss"', chart)
        self.assertIn('left:10.000%;width:40.000%', chart)
        for key, invalid in [('period_end', '2026-12-31'), ('currency', 'EUR'),
                             ('reported_net_previous_period_end', '2024-06-30'),
                             ('reported_net_label', 'Résultat total'), ('reported_net_millions', None)]:
            self.assertEqual(semester_chart({**data, key: invalid}), '', key)
        self.assertEqual(semester_chart({**data, 'reported_net_previous_period_end': None}), '')


if __name__ == '__main__':
    unittest.main()
