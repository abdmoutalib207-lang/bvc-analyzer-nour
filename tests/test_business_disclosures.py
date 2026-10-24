"""Evidence, dimensional and temporal boundaries for published business figures."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from nour.business_disclosures import attach_business_facts, disclosure_view, load_catalogue
from nour.sector_calculators import calculate_sector
from nour.sector_view import business_disclosures_card

ROOT = Path(__file__).resolve().parents[1]


class BusinessDisclosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogues = load_catalogue(ROOT/'knowledge/business_disclosures')
        cls.raw = cls.catalogues['MNG']
        cls.facts = json.loads((ROOT/'data/facts_reference.json').read_text())['records']

    def test_reviewed_figures_keep_dimensions_scopes_and_source_precision(self):
        view = disclosure_view(self.raw, '2026-10-24')
        rows = {r['id']: r for r in view['records']}
        self.assertEqual(len(rows), 74)
        self.assertTrue(all(r['status'] == 'primary_page_checked' for r in rows.values()))
        for key, value, unit in [('copper-group-2025',110721,'TC'), ('silver-group-2025',150810,'kg'),
                                 ('gold-group-2025',6717,'kg'), ('cobalt-2025',507,'TM'),
                                 ('cash-capex-2025',-5950,'MDH'), ('cash-capex-2024',-7254.4,'MDH'),
                                 ('cash-capex-s1-2026',-1731,'MDH'), ('cash-capex-s1-2025',-2885.5,'MDH'), ('cash-change-s1-2025',-567.5,'MDH'),
                                 ('investment-total-2024',7224.2,'MDH'), ('materials-2024',-4301,'MDH')]:
            self.assertEqual((rows[key]['value'],rows[key]['unit']), (value,unit), key)
        self.assertEqual(rows['copper-group-2025']['quantity_basis'], 'concentrate')
        self.assertEqual(rows['cash-capex-s1-2025']['page'],15)
        self.assertEqual(rows['copper-group-2025']['page'],66)
        self.assertNotIn('copper-cmo-2025',rows, 'A blank published cell must not become zero')
        self.assertTrue(all(r['used_for_score'] is False for r in rows.values()))

    def test_bad_evidence_or_physical_dimensions_cannot_be_published_as_numbers(self):
        for field,value in [('value',True),('value',float('nan')),('unit','MAD'),
                            ('period_end','2027-12-31'),('period_kind','TTM'),('page',False),
                            ('quantity_basis','contained_metal'),('scope','')]:
            broken=deepcopy(self.raw);broken['records'][0][field]=value
            result=disclosure_view(broken,'2026-10-24')['records'][0]
            self.assertIsNone(result['value'],field);self.assertEqual(result['status'],'unavailable')
        for field,value in [('url','https://unverified.example/report.pdf'),('document_hash','sha256:wrong')]:
            broken=deepcopy(self.raw);broken['documents']['annual25'][field]=value
            self.assertIsNone(disclosure_view(broken,'2026-10-24')['records'][0]['value'])
        broken=deepcopy(self.raw);broken['records'].append(deepcopy(broken['records'][0]))
        self.assertIsNone(disclosure_view(broken,'2026-10-24')['records'][-1]['value'])

    def test_no_backfill_before_actual_review_and_no_input_mutation(self):
        before=deepcopy(self.facts)
        enriched=attach_business_facts(self.facts,self.catalogues,'2026-10-24')
        self.assertEqual(self.facts,before)
        for symbol,record in before.items():
            self.assertEqual(record['faits'],enriched[symbol]['faits'])
            if symbol!='MNG':self.assertEqual(record,enriched[symbol])
        old=attach_business_facts(self.facts,self.catalogues,'2026-10-23')['MNG']
        self.assertEqual(disclosure_view(old['business_disclosures'],'2026-10-23')['records'],[])
        self.assertNotIn('capex_decaisse',old.get('sector_faits',{}))
        current=enriched['MNG']['sector_faits']['capex_decaisse']
        self.assertEqual((current['valeur'],current['valeur_au_rapport']), (5950,-5950))
        self.assertEqual(current['normalization'],'cash_outflow_to_positive_capex')

    def test_production_is_displayed_without_manufacturing_a_unit_cost(self):
        enriched=attach_business_facts(self.facts,self.catalogues,'2026-10-24')
        sector=calculate_sector('MNG',{},enriched['MNG'],'2026-10-24')
        self.assertEqual(sector['published_kpis']['production_miniere']['status'],'published_breakdown')
        self.assertIsNone(sector['metrics']['mine_unit_cost']['value'])
        self.assertEqual(sector['published_kpis']['capex_decaisse']['value'],5950)
        card=business_disclosures_card(sector['business_disclosures'])
        self.assertIn('110 721 TC',card);self.assertIn('-2 885,5 MDH',card)
        self.assertIn('#page=66',card);self.assertIn('page PDF 15',card)
        self.assertIn('41 %',card)

    def test_html_escapes_documentary_text_and_does_not_link_invalid_proof(self):
        view=disclosure_view(self.raw,'2026-10-24')
        view['records'][0]['label']='<script>alert(1)</script>'
        view['records'][0]['status']='unavailable'
        view['records'][0]['source']['url']='javascript:alert(1)'
        card=business_disclosures_card(view)
        self.assertNotIn('<script>',card);self.assertNotIn('javascript:',card)
        self.assertIn('&lt;script&gt;',card)
