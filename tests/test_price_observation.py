from copy import deepcopy
import unittest

from nour.engine import build_report, _price_observation
from nour.issuer_view import issuer_heading
from nour.quote_view import quote_view, quote_clocks
from nour.assistant import build_data


ASOF = '2026-11-08'


def inputs():
    bar = dict(d='2026-11-05', o=37, h=38.7, l=37, c=38.7, v=100, turnover_mad=3800)
    record = dict(symbol='ADH', name='Addoha', sector='Immobilier', price=38.7,
                  price_asof=bar['d'], stale=False, suspended=False,
                  day_shares=100, day_turnover_mad=3800,
                  price_source='CDG Capital Bourse',
                  candles=[dict(d='2026-11-04', o=37, h=37.1, l=36.5, c=37.1, v=50), bar])
    primary = {**bar, 'v': 90, 'turnover_mad': 3413}
    record['quarantined_market'] = dict(symbol='ADH', session=bar['d'], domain='volume',
        code='market_line_quarantined', source='https://www.cdgcapitalbourse.ma/api/',
        reason='Quantité ou montant en conflit', observed_at='2026-11-08T13:00:00Z',
        observed={'primary': primary, 'secondary': None})
    fixture = dict(project='Nour', schema_version=2, snapshot_updated='2026-11-08T12:00:00Z',
                   source_commit='a'*40, source_files={}, symbols=['ADH'], records={'ADH': record})
    def fact(value, unit='MMAD'):
        return dict(valeur=value, unite=unit, period_end='2025-12-31', base='consolidé IFRS',
                    devise='MAD', page=2, url='https://issuer.example/results.pdf',
                    document_hash='sha256:'+'b'*64, validation_status='selected_pages_visually_checked')
    facts = {'ADH': dict(exercice=2025, exercice_clos='2025-12-31', devise='MAD',
        url='https://issuer.example/results.pdf', accounting_basis='consolidé IFRS',
        faits={'resultat_net_part_groupe':fact(20), 'capitaux_propres_part_groupe':fact(200),
               'nombre_actions':fact(10000000, 'actions')})}
    return fixture, facts


class PriceObservationTests(unittest.TestCase):
    def test_price_proof_prices_audited_ratios_without_releasing_volume_or_score(self):
        fixture, facts = inputs(); before = deepcopy((fixture, facts))
        row = build_report(fixture, ASOF, facts=facts)['results'][0]
        proof = row['price_observation']
        self.assertEqual(proof['price'], 38.7)
        self.assertEqual(proof['asof'], '2026-11-05')
        self.assertEqual(proof['collected_at'], '2026-11-08T13:00:00Z')
        self.assertEqual(proof['status'], 'price_fields_match_volume_disputed')
        self.assertFalse(proof['cross_source_verified'])
        self.assertIsNone(row['price']); self.assertIsNone(row['day_shares'])
        self.assertIsNone(row['day_turnover_mad_actual']); self.assertIsNone(row['canonical_score']['value'])
        self.assertIsNone(row['technical']['sma20']); self.assertFalse(row['liquidity']['ready'])
        self.assertEqual(row['historical_statistics']['status'], 'unavailable')
        self.assertEqual(row['fundamental']['pe'], 19.35)
        self.assertEqual(row['fundamental']['pb'], 1.94)
        self.assertEqual(row['fundamental']['quote_valuation'], proof)
        self.assertEqual((fixture, facts), before)
        report = build_report(fixture, ASOF, facts=facts)
        exported = build_data(report)['symbols']['ADH']
        self.assertEqual(exported['price_observation'], proof)
        self.assertEqual(exported['fundamental']['quote_valuation'], proof)

    def test_financial_block_still_withholds_per_at_usable_observed_price(self):
        fixture, facts = inputs()
        facts['ADH']['calculation_reservations'] = [dict(status='unresolved', metrics=['pe'],
            fields=['nombre_actions'], detail='Dénominateur contesté')]
        row = build_report(fixture, ASOF, facts=facts)['results'][0]
        self.assertEqual(row['price_observation']['price'], 38.7)
        self.assertIsNone(row['fundamental']['pe'])
        self.assertEqual(row['fundamental']['pb'], 1.94)
        self.assertIn('pe', row['fundamental']['financial_audit']['blocked_metrics'])

    def test_changed_primary_price_keeps_valuation_and_display_unavailable(self):
        fixture, facts = inputs()
        fixture['records']['ADH']['quarantined_market']['observed']['primary']['c'] = 38.6
        row = build_report(fixture, ASOF, facts=facts)['results'][0]
        self.assertNotIn('price_observation', row)
        self.assertNotIn('quote_valuation', row['fundamental'])
        self.assertIsNone(row['fundamental']['pe'])
        self.assertIsNone(row['fundamental']['pb'])
        self.assertIsNone(quote_view(row, fixture['records']['ADH'])['price'])

    def test_price_conflicts_identity_and_invalid_clocks_never_create_proof(self):
        fixture, _ = inputs(); original = fixture['records']['ADH']
        cases = []
        r=deepcopy(original); r['quarantined_market']['observed']['primary']['c']=38.6; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['observed']['primary']['h']=39; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['symbol']='RDS'; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['source']='https://elsewhere.example/api/'; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['observed_at']='2026-11-09T13:00:00Z'; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['observed_at']='2026-11-08T13:00:00'; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['session']='2026-11-04'; cases.append(r)
        r=deepcopy(original); r['quarantined_market']['observed']['secondary']={'session':'2026-11-05','price':39}; cases.append(r)
        r=deepcopy(original); r['candles'].append(deepcopy(r['candles'][-1])); cases.append(r)
        r=deepcopy(original); r['price']=True; cases.append(r)
        for i, record in enumerate(cases):
            with self.subTest(case=i):
                self.assertIsNone(_price_observation(record, ASOF))

    def test_issuer_shows_numeric_price_with_volume_notice_and_its_own_collection(self):
        fixture, facts=inputs(); record=fixture['records']['ADH']
        row=build_report(fixture, ASOF, facts=facts)['results'][0]
        view=quote_view(row,record)
        self.assertTrue(view['observed_only'])
        self.assertEqual(view['price'],38.7)
        self.assertEqual(view['label'],'Cours publié · volume à vérifier')
        self.assertTrue(view['validation_unavailable'])
        self.assertIsNone(view['price_validated_at'])
        page=issuer_heading(row,record)
        self.assertIn('data-primary-price>38,70',page)
        self.assertIn('Cours disponible · volume à vérifier',page)
        self.assertIn('08/11/2026',quote_clocks(view))
        self.assertIn('quantité et montant échangés non validés',page)
        self.assertNotIn('Dernière cotation validée',page)
