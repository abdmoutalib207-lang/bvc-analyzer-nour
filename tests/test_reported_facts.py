from copy import deepcopy
import unittest
from nour.reported_facts import reported_facts
from nour.sector_view import reported_facts_card

class ReportedFactsTests(unittest.TestCase):
    def sample(self):
        return dict(exercice=2025,url='https://www.ammc.ma/report.pdf',faits={
            'resultat_net_part_groupe':dict(valeur=12,page=2,base='social',note='Réserve documentaire'),
            'capex_decaisse':dict(valeur=3,unite='MMAD',valeur_au_rapport=-3000,unite_au_rapport='KMAD',period_end='2025-12-31',page=4)},
            financial_review={'conclusion':'Dette non rapprochée'},latest_report={
                'period_end':'2026-06-30','document_url':'https://www.ammc.ma/semi.pdf',
                'reported_net_millions':5,'currency':'TND','accounting_basis':'résultat total, pas RNPG'})
    def test_unknown_unit_and_original_sign_are_visible_without_promoting_a_ratio(self):
        f=self.sample();before=deepcopy(f);r=reported_facts(f,'2026-10-24')
        self.assertEqual(f,before)
        self.assertEqual(r['records'][0]['unit'],'unité à préciser')
        self.assertIn('social',r['records'][0]['label'])
        self.assertEqual(r['records'][1]['value'],-3000)
        self.assertEqual(r['records'][1]['unit'],'KMAD')
        self.assertEqual(r['records'][2]['unit'],'millions de TND')
        self.assertTrue(all(x['status']=='referenced_to_review' and x['used_for_score'] is False for x in r['records']))
        self.assertIn('Dette non rapprochée',r['reservations'])
    def test_invalid_source_future_and_nonfinite_do_not_produce_numbers(self):
        f=self.sample();f['faits']['resultat_net_part_groupe']['valeur']=True
        f['faits']['capex_decaisse']['period_end']='2028-12-31'
        f['latest_report']['document_url']='javascript:alert(1)'
        self.assertEqual(reported_facts(f,'2026-10-24')['records'],[])
    def test_html_preserves_reservations_and_escapes_text(self):
        f=self.sample();f['faits']['capex_decaisse']['note']='<script>bad</script>'
        card=reported_facts_card(reported_facts(f,'2026-10-24'))
        self.assertIn('Dette non rapprochée',card);self.assertIn('unité à préciser',card)
        self.assertNotIn('<script>',card);self.assertIn('-3 000 KMAD',card)
