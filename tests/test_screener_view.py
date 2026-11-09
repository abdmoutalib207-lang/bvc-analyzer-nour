from copy import deepcopy
import unittest

from nour.screener_view import body, summary_card, visible_state


def sample():
    return dict(status='collected', checked_at='2026-11-09T12:00:00Z',
        last_success_at='2026-11-09T12:00:00Z', source_generated_at='2026-11-05',
        source_sha256='a'*64, nour_facts_sha256='b'*64,
        summary=dict(agreement=1, rounding=0, difference=0, not_comparable=0, missing=0, issuers=1, rows=1),
        rows=[dict(symbol='ADI', metric='RNPG', nour_field='resultat_net_part_groupe',
            period='FY2025', period_end='2025-12-31', unit='MMAD', scope='consolidé',
            nour_value=407.6, screener_value=407.6, difference=0, status='agreement',
            reason='Même période et même base', screener_regime='PCGI 2025',
            nour_provenance=dict(url='https://www.ammc.ma/sites/default/files/ADI_RFA_2025.pdf',
                page=22, document_hash='sha256:'+'c'*64, validation_status='selected_pages_visually_checked',
                base='consolidé national', period_end='2025-12-31'),
            screener_provenance=dict(document='RFA 2025', page=22, label='Part du Groupe',
                method='text_parse', version='reported', provenance_grade='label_page_only'))], notices=[])


class ScreenerViewTests(unittest.TestCase):
    def test_all_agreements_are_auditable_without_promoting_external_provenance(self):
        state=sample(); before=deepcopy(state); page=body(state, '2026-11-09')
        for text in ('Résultat net part du groupe', 'FY2025', 'MMAD', 'consolidé', '407,6', 'Concordance numérique',
                     'Part du Groupe', 'RFA 2025', 'PCGI 2025', 'sha256:'+'c'*64,
                     'Aucune correction automatique', 'Aucun document certifié', '80 sociétés Nour'):
            self.assertIn(text, page)
        self.assertIn('href="https://www.ammc.ma/sites/default/files/ADI_RFA_2025.pdf"', page)
        self.assertNotIn('href="RFA 2025"', page)
        self.assertIn('<h1>Contre-vérification financière</h1>', page)
        self.assertIn('data-screener-audit', page)
        self.assertIn('data-comparison-symbol="ADI"', page)
        self.assertEqual(state, before)

    def test_source_links_are_exact_official_origins_and_untrusted_text_escaped(self):
        for url in ('javascript:alert(1)', 'http://www.ammc.ma/a',
                    'https://www.ammc.ma.evil.test/a', 'https://www.ammc.ma@evil.test/a',
                    'https://www.ammc.ma:444/a', 'https://evil.test/a',
                    'https://www.ammc.ma/a\n"onclick="bad'):
            with self.subTest(url=url):
                state=sample(); row=state['rows'][0]
                row['nour_provenance']['url']=url
                row['screener_provenance']['document']='<script>alert(1)</script>'
                row['reason']='<img src=x onerror=bad>'
                row['symbol']='ADI"><script>bad</script>'
                page=body(state, '2026-11-09')
                self.assertNotIn('<script>', page); self.assertNotIn('<img ', page)
                self.assertIn('&lt;script&gt;', page)
                self.assertIn('lien absent ou non autorisé', page)

    def test_future_snapshot_is_not_shown_at_past_analysis_date(self):
        for key in ('checked_at', 'last_success_at', 'source_generated_at'):
            state=sample(); state[key]='2026-11-10T00:00:00Z'
            out=visible_state(state, '2026-11-09', 'b'*64)
            self.assertEqual(out['status'], 'not_yet_available')
            self.assertEqual(out['rows'], []); self.assertEqual(out['summary']['agreement'], 0)
            page=body(out, '2026-11-09')
            self.assertNotIn('407,6', page)
            self.assertIn('État postérieur', page)

    def test_future_financial_period_is_excluded_without_erasing_past_rows(self):
        state=sample(); future=deepcopy(state['rows'][0]);future['period_end']='2027-12-31'
        state['rows'].append(future)
        out=visible_state(state, '2026-11-09')
        self.assertEqual(len(out['rows']),1);self.assertEqual(out['summary']['agreement'],1)
        self.assertTrue(any('périodes financières' in n for n in out['notices']))

    def test_stale_degraded_and_changed_inputs_keep_observations_explicitly_dated(self):
        state=sample();state['status']='degraded';state['collection_error_code']='source_unavailable'
        page=body(state, '2026-11-09')
        self.assertIn('Collecte dégradée',page);self.assertIn('source_unavailable',page)
        self.assertIn('2026-11-09T12:00:00Z',page);self.assertIn('407,6',page)
        old=visible_state(state,'2026-11-20','b'*64)
        self.assertEqual(old['status'],'stale')
        self.assertIn('11 jours', ' '.join(old['notices']))
        changed=visible_state(state,'2026-11-09','d'*64)
        self.assertEqual(changed['status'],'stale_inputs')
        self.assertEqual(changed['rows'],state['rows'])
        self.assertIn('relancer',body(changed,'2026-11-09'))

    def test_missing_external_and_scope_conflicts_remain_readable(self):
        state=sample();row=state['rows'][0]
        row.update(status='not_comparable', reason='Périmètre social contre consolidé',
                   screener_value=None, difference=None,scope='social / consolidé')
        page=body(state,'2026-11-09')
        self.assertIn('Bases non comparables',page);self.assertIn('social / consolidé',page)
        row.update(status='missing',reason='Société absente de la source externe')
        self.assertIn('Donnée manquante',body(state,'2026-11-09'))

    def test_summary_and_absent_state_are_non_blocking_and_no_nonfinite_numbers_rendered(self):
        self.assertIn('non encore exécutée',body(None,'2026-11-09'))
        self.assertEqual(visible_state(None,'2026-11-09','b'*64)['status'],'not_observed')
        self.assertEqual(visible_state({},'2026-11-09','b'*64)['status'],'not_observed')
        self.assertIn('contre-verification.html',summary_card(sample(),'2026-11-09'))
        for value in (True, float('nan'), float('inf')):
            state=sample();state['rows'][0]['nour_value']=value
            page=body(state,'2026-11-09')
            self.assertNotIn('<td>True</td>',page);self.assertNotIn('<td>nan</td>',page)
            self.assertNotIn('<td>inf</td>',page)

    def test_rendering_prepared_state_does_not_repeat_reservations(self):
        state=visible_state(sample(),'2026-11-20','d'*64)
        page=body(state,'2026-11-20')
        self.assertEqual(page.count('Dernier succès ancien :'),1)
        self.assertEqual(page.count('Les faits Nour ont changé'),1)
        self.assertIn('Données Nour modifiées depuis la comparaison',page)

    def test_difference_sign_export_path_and_french_reason_match_collector_contract(self):
        state=sample();row=state['rows'][0]
        row.update(metric='CA',nour_value=12,screener_value=10,difference=-2,
                   scope='consolidated',status='difference',reason='primary_document_review_required')
        page=body(state,'2026-11-09')
        self.assertIn('Écart MS − Nour',page);self.assertNotIn('Écart Nour − MS',page)
        self.assertIn('<td>12</td><td>10</td><td>-2</td>',page)
        self.assertIn('href="screener-reconciliation.json"',page)
        self.assertNotIn('href="screener-comparison.json"',page)
        self.assertIn('Chiffre d’affaires',page);self.assertIn('Comptes consolidés',page)
        self.assertIn('Écart à vérifier dans les documents officiels',page)
        self.assertNotIn('primary_document_review_required',page)

    def test_missing_coverage_explains_target_counts_and_future_state_hides_it(self):
        state=sample()
        state['summary'].update(issuers=80,source_issuers=78,nour_issuers=77,compared_issuers=76)
        state['coverage']=[dict(symbol='ADI',status='available',nour_available=True),
                           dict(symbol='DIS',status='source_missing',nour_available=False),
                           dict(symbol='IBM',status='nour_missing',nour_available=False),
                           dict(symbol='CFGB',status='identity_review_required',nour_available=True)]
        page=body(state,'2026-11-09')
        self.assertIn('Univers suivi : <strong>80</strong>',page)
        self.assertIn('Sociétés présentes dans la source : <strong>78</strong>',page)
        self.assertIn('Dossiers financiers Nour : <strong>77</strong>',page)
        self.assertIn('Sociétés avec lignes de comparaison : <strong>76</strong>',page)
        self.assertIn('Lignes non comparées',page);self.assertIn('DIS',page);self.assertIn('IBM',page)
        self.assertIn('Société absente de la source externe',page)
        self.assertIn('Dossier financier Nour absent',page)
        self.assertIn('Identité de la société à rapprocher',page)
        future=visible_state(state,'2026-11-08')
        self.assertEqual(future['coverage'],[])
        future_page=body(future,'2026-11-08')
        self.assertNotIn('Lignes non comparées',future_page)
        self.assertNotIn('<strong>78</strong>',future_page)


if __name__ == '__main__':
    unittest.main()
