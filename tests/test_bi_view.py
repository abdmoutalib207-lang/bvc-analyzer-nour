import copy
import unittest

from nour.bi_view import financial_dashboard, semester_chart


class BiViewTests(unittest.TestCase):
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
        self.assertIn('3 / 7 indicateurs affichables', page)

    def test_loss_is_explained_and_unsafe_source_is_not_a_link(self):
        page = financial_dashboard({'fundamental': {'earnings_mmad': -10,
            'document_url': 'javascript:alert(1)', 'roe_method': '<script>bad</script>'}})
        self.assertIn('Une perte publiée n’est pas une donnée manquante', page)
        self.assertNotIn('href="javascript:', page)
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_missing_and_non_finite_values_are_not_displayed_as_zero(self):
        page = financial_dashboard({'fundamental': {'pe': float('nan'), 'roe_pct': True}})
        self.assertIn('0 / 7 indicateurs affichables', page)
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
        self.assertIn('1 / 8 indicateurs affichables', page)
        # Missing PNB does not suppress independently available EPS.
        self.assertIn('>3,40<', page)
        for family in ('Finance - crédit-bail', 'Finance - crédit à la consommation'):
            self.assertIn('Croissance du PNB',
                          financial_dashboard({'sector_guidance': {'family': family},
                                               'fundamental': {}}))

    def test_unreasonably_large_integer_is_not_rendered_as_a_valid_number(self):
        page = financial_dashboard({'fundamental': {'pe': 10 ** 1000}})
        self.assertIn('0 / 7 indicateurs affichables', page)

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
