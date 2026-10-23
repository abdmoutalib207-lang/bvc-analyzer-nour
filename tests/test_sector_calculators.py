from copy import deepcopy
import json
from pathlib import Path
import unittest
from nour.sector_calculators import calculate_sector
from nour.sector_validation import audit_sector_calculations
from tools.import_sector_oct23 import reconcile
ROOT=Path(__file__).resolve().parents[1]

def fact(value,**extra):
    return dict(valeur=value,unite='MMAD',base='consolidé IFRS',devise='MAD',period_end='2025-12-31',
        page=7,validation_status='selected_pages_visually_checked',document_hash='sha256:'+'a'*64,url='https://www.ammc.ma/report.pdf',**extra)
def inputs(values,contract=None):
    return dict(exercice=2025,exercice_clos='2025-12-31',accounting_basis='consolidé IFRS',
        faits={k:fact(v,**({'definition_contract':contract} if contract else {})) for k,v in values.items()})

class SectorCalculatorTests(unittest.TestCase):
    def test_bank_cost_income_and_non_industrial_exclusion(self):
        f=inputs({'charges_generales_exploitation':45,'produit_net_bancaire':100},'bank_cost_income')
        m=calculate_sector('ATW',{},f,'2026-10-23')['metrics']
        self.assertEqual(m['cost_income_pct']['value'],45)
        self.assertNotIn('ebitda_margin_pct',m)
        self.assertNotIn('roic_pct',m)
        f['faits']['charges_generales_exploitation']['definition_contract']='wrong_scope'
        self.assertIsNone(calculate_sector('ATW',{},f,'2026-10-23')['metrics']['cost_income_pct']['value'])

    def test_credit_consumer_and_holding_are_not_industrial(self):
        for s in ('DIS','EQD','SLM','MGL','MRL','DHO'):
            m=calculate_sector(s,{},inputs({}),'2026-10-23')['metrics']
            self.assertNotIn('ebitda_margin_pct',m,s)
            self.assertNotIn('roic_pct',m,s)

    def test_primary_business_kpi_is_not_inferred_or_scored(self):
        f=inputs({'produit_net_bancaire':100})
        k=calculate_sector('ATW',{},f,'2026-10-23')['published_kpis']['produit_net_bancaire']
        self.assertEqual(k['value'],100);self.assertFalse(k['used_for_score'])
        f['faits']['produit_net_bancaire']['validation_status']='referenced_import'
        self.assertIsNone(calculate_sector('ATW',{},f,'2026-10-23')['published_kpis']['produit_net_bancaire']['value'])

    def test_insurance_same_nonlife_contract(self):
        f=inputs({'sinistres_survenus_non_vie':60,'frais_techniques_non_vie':20,'primes_acquises_non_vie':100},'nonlife_same_reinsurance_basis')
        m=calculate_sector('WAF',{},f,'2026-10-23')['metrics']
        self.assertEqual(m['combined_ratio_pct']['value'],80)
        f['faits']['primes_acquises_non_vie']['base']='social (normes marocaines)'
        self.assertIsNone(calculate_sector('WAF',{},f,'2026-10-23')['metrics']['combined_ratio_pct']['value'])

    def test_btp_backlog_is_years_not_future_profit(self):
        f=inputs({'carnet_commandes':1500,'commandes_nouvelles':700,'chiffre_affaires':500})
        m=calculate_sector('TGCC',{},f,'2026-10-23')['metrics']
        self.assertEqual(m['backlog_revenue_years']['value'],3)
        self.assertEqual(m['book_to_bill']['value'],1.4)
        self.assertFalse(m['book_to_bill']['used_for_score'])

    def test_missing_is_not_zero_and_units_period_scope_proofs_are_strict(self):
        f=inputs({'resultat_exploitation':10,'chiffre_affaires':100})
        for field,value in [('unite','KMAD'),('period_end','2025-06-30'),('validation_status','extracted'),('valeur',True),('document_hash',None),('page',None)]:
            broken=deepcopy(f);broken['faits']['chiffre_affaires'][field]=value
            self.assertIsNone(calculate_sector('AKD',{},broken,'2026-10-23')['metrics']['operating_margin_pct']['value'],field)
        self.assertIsNone(calculate_sector('AKD',{},inputs({}),'2026-10-23')['metrics']['operating_margin_pct']['value'])
        f['faits']['resultat_exploitation']['valeur']=-10
        self.assertEqual(calculate_sector('AKD',{},f,'2026-10-23')['metrics']['operating_margin_pct']['value'],-10)

    def test_original_amount_and_cash_sign_must_reconcile(self):
        f=inputs({'flux_tresorerie_exploitation':10,'capex_decaisse':3,'chiffre_affaires':100})
        f['faits']['capex_decaisse'].update(valeur_au_rapport=-3000000,unite_au_rapport='MAD',normalization='cash_outflow_to_positive_capex')
        self.assertEqual(calculate_sector('AKD',{},f,'2026-10-23')['metrics']['free_cash_after_capex_mmad']['value'],7)
        f['faits']['capex_decaisse']['valeur_au_rapport']=3000000
        self.assertIsNone(calculate_sector('AKD',{},f,'2026-10-23')['metrics']['free_cash_after_capex_mmad']['value'])
        f['faits']['capex_decaisse']['valeur_au_rapport']=-3000
        self.assertIsNone(calculate_sector('AKD',{},f,'2026-10-23')['metrics']['free_cash_after_capex_mmad']['value'])

    def test_hotel_money_and_room_nights_keep_their_dimensions(self):
        f=inputs({'revenu_chambres_mad':1200,'nuitees_chambres_vendues':10,'nuitees_chambres_disponibles':20},'hotel_room_nights')
        f['faits']['revenu_chambres_mad'].update(unite='MAD',valeur_au_rapport=1.2,unite_au_rapport='KMAD')
        for name in ('nuitees_chambres_vendues','nuitees_chambres_disponibles'):
            f['faits'][name].update(unite='chambres',valeur_au_rapport=f['faits'][name]['valeur'],unite_au_rapport='chambres')
        m=calculate_sector('RIS',{},f,'2026-10-23')['metrics']
        self.assertEqual(m['hotel_adr_mad']['value'],120)
        self.assertEqual(m['hotel_revpar_mad']['value'],60)
        self.assertEqual(m['hotel_occupancy_pct']['value'],50)

    def test_primary_replay_preserves_legacy_facts_and_scores_inputs(self):
        payload=json.loads((ROOT/'data/facts_reference.json').read_text())
        review=json.loads((ROOT/'knowledge/financial_reviews/2026-10-23-sector.json').read_text())
        changed=reconcile(payload,review)
        self.assertEqual(changed,payload)
        for s,old in payload['records'].items():
            self.assertEqual(old['faits'],changed['records'][s]['faits'])
        f=changed['records']['AKD'];m=calculate_sector('AKD',{},f,'2026-10-23')['metrics']
        self.assertAlmostEqual(m['operating_cash_margin_pct']['value'],3.4482)
        self.assertEqual(m['free_cash_after_capex_mmad']['value'],-2066.1245)
        self.assertEqual(f['sector_faits']['capex_decaisse']['valeur_au_rapport'],-2218304904)
        self.assertEqual(f['sector_faits']['capex_decaisse']['normalization'],'cash_outflow_to_positive_capex')
        audit=audit_sector_calculations({'results':[{'symbol':'AKD','sector_indicators':{'metrics':m}}]})
        self.assertFalse(audit['failures']);self.assertGreater(audit['arithmetic_checks'],4)
        m['operating_margin_pct']['value']=999
        self.assertEqual(audit_sector_calculations({'results':[{'symbol':'AKD','sector_indicators':{'metrics':m}}]})['failures'][0]['metric'],'operating_margin_pct')
