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

    def test_same_documented_fact_in_both_archives_is_shown_once_with_origins(self):
        facts=self.sample()
        facts['sector_faits']={'capex_decaisse':deepcopy(facts['faits']['capex_decaisse'])}
        before=deepcopy(facts)
        report=reported_facts(facts,'2026-10-24')
        rows=[r for r in report['records'] if r['id'].endswith('capex_decaisse')]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['origins'],['faits','sector_faits'])
        self.assertEqual(rows[0]['value'],-3000)
        self.assertEqual(rows[0]['source']['page'],4)
        self.assertEqual(facts,before)
        card=reported_facts_card(report)
        self.assertEqual(card.count('-3 000 KMAD'),1)

    def test_disagreements_and_distinct_periods_scopes_or_sources_are_retained(self):
        for field,value in [('valeur',4),('valeur_au_rapport',-4000),('period_end','2024-12-31'),
                            ('unite','MAD'),('unite_au_rapport','MAD'),('base','consolidé IFRS'),
                            ('url','https://www.ammc.ma/other.pdf'),('page',5),
                            ('document_hash','sha256:'+'a'*64),('note','Réserve nouvelle')]:
            facts=self.sample()
            facts['sector_faits']={'capex_decaisse':{**facts['faits']['capex_decaisse'],field:value}}
            rows=[r for r in reported_facts(facts,'2026-10-24')['records'] if r['id'].endswith('capex_decaisse')]
            self.assertEqual(len(rows),2,field)
            self.assertEqual(rows[0]['origins'],['faits'])
            self.assertEqual(rows[1]['origins'],['sector_faits'])
