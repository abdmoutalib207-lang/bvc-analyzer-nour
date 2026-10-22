import copy
import unittest

from nour.issuer_view import financial_history, issuer_heading


class IssuerPresentationTests(unittest.TestCase):
    def setUp(self):
        self.item = {'fundamental': {'period_end': '2025-12-31', 'currency': 'MAD', 'evidence': {
            'chiffre_affaires': {'value': 120, 'period_end': '2025-12-31', 'unit': 'MMAD',
                                'currency': 'MAD', 'accounting_basis': 'Consolidé IFRS',
                                'document_url': 'https://example.org/annual.pdf', 'page': 22},
            'chiffre_affaires_2024': {'value': 100, 'period_end': '2024-12-31', 'unit': 'MMAD',
                                     'currency': 'MAD', 'accounting_basis': 'Consolidé IFRS',
                                     'document_url': 'https://example.org/annual.pdf', 'page': 22}}}}

    def test_only_compatible_dated_comparatives_are_drawn_without_mutating_facts(self):
        before = copy.deepcopy(self.item)
        output = financial_history(self.item)
        self.assertIn('financial-history-grid', output)
        self.assertIn('2024-12-31', output)
        self.assertIn('120,00 MMAD au 2025-12-31', output)
        self.assertIn('annual.pdf#page=22', output)
        self.assertEqual(before, self.item)
        for field, bad in [('period_end', '2025-06-30'), ('unit', 'KMAD'),
                           ('currency', 'EUR'), ('accounting_basis', 'Social'),
                           ('document_url', 'https://example.org/other.pdf'),
                           ('page', None), ('value', float('nan'))]:
            changed = copy.deepcopy(self.item)
            changed['fundamental']['evidence']['chiffre_affaires_2024'][field] = bad
            self.assertNotIn('financial-history-grid', financial_history(changed), field)

    def test_zero_and_negative_amounts_remain_observations(self):
        self.item['fundamental']['evidence']['chiffre_affaires']['value'] = 0
        self.item['fundamental']['evidence']['chiffre_affaires_2024']['value'] = -20
        output = financial_history(self.item)
        self.assertIn('-20,00 MMAD', output)
        self.assertIn('0,00 MMAD', output)
        self.assertNotRegex(output, r'(?:x|y|height)="(?:nan|inf)"')

    def test_header_dates_change_as_previous_available_close_not_assumed_yesterday(self):
        item = {'symbol': 'ADI', 'price': 110, 'asof': '2026-10-16', 'decision': 'OBSERVABLE',
                'price_source': 'Source test', 'history_readiness': {'label': '2 séances'}}
        record = {'name': '<Titre>', 'sector': 'Test', 'candles': [
            {'d': '2026-10-01', 'c': 100}, {'d': '2026-10-16', 'c': 110}]}
        output = issuer_heading(item, record)
        self.assertIn('+10,00 %', output)
        self.assertIn('clôture disponible du 01/10/2026', output)
        self.assertIn('&lt;Titre&gt;', output)
        for key in ['graphique', 'technique', 'fondamentaux', 'risques', 'historique']:
            self.assertIn(f'href="#{key}"', output)
        item['asof'] = '2026-10-15'
        self.assertNotIn('quote-change', issuer_heading(item, record))
