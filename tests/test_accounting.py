"""Source-specific accounting, temporal boundaries and unchanged canonical results."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from nour.accounting import catalog, declaration, profile, validate_catalog
from nour.assistant import build_data, context_for
from nour.engine import build_report

ROOT = Path(__file__).resolve().parents[1]


class AccountingMethods(unittest.TestCase):
    def annual(self, symbol):
        review = catalog()['issuers'][symbol]
        labels = {'ifrs':'consolidé IFRS', 'moroccan':'consolidé (normes marocaines)',
                  'moroccan_credit':('Social, plan comptable des établissements de crédit'
                                    if review['scope']=='social' else 'Consolidé, comptes des établissements de crédit')}
        source = catalog()['sources'][review['source']]
        return dict(accounting_basis=labels[review['framework']], period_end=review['period_end'],
                    exercise=2025, document_url=source['url'], provenance={}, latest_report=None)

    def test_sector_never_supplies_a_missing_standard(self):
        for sector in ('Banque','Assurance','Immobilier','Technologie'):
            p = profile('XYZ',{},sector,'2026-10-26')
            self.assertEqual(p['framework'],'unknown')
            self.assertEqual(p['status'],'missing')
            self.assertFalse(p['policies'])

    def test_social_credit_and_foreign_frameworks_stay_distinct(self):
        self.assertEqual(declaration('SOCIAL normes marocaines, aucun compte consolidé'),('social','moroccan'))
        self.assertEqual(declaration('Consolidé IFRS, les comptes sociaux sont distincts'),('consolidated','ifrs'))
        self.assertEqual(declaration('Social, PCEC'),('social','moroccan_credit'))
        self.assertEqual(declaration('consolidé, système comptable tunisien SCE, TND'),('consolidated','tunisian'))
        self.assertEqual(declaration({'scope':'not a source label'}),('unknown','unknown'))

    def test_each_review_is_scoped_to_its_company_and_annual_document(self):
        for symbol,review in catalog()['issuers'].items():
            with self.subTest(symbol=symbol):
                p = profile(symbol,self.annual(symbol),'', '2026-10-26')
                self.assertEqual(p['status'],'primary_scoped_review')
                self.assertEqual(p['scope'],review['scope'])
                self.assertEqual(p['framework'],review['framework'])
                self.assertFalse(p['documents_certified']); self.assertFalse(p['used_for_score'])
                self.assertEqual(p['evidence'][0]['page'],review['basis_page'])

    def test_source_change_and_new_period_never_inherit_visual_review(self):
        for change in ({'period_end':'2026-12-31','exercise':2026},
                       {'document_url':'https://www.ammc.ma/new.pdf'},
                       {'provenance':{'document_hash':'sha256:'+'0'*64}}):
            f = {**self.annual('HPS'),**change}
            p = profile('HPS',f,'Technologie','2027-10-26')
            self.assertNotEqual(p['status'],'primary_scoped_review')
            self.assertFalse(p['policies'])

    def test_review_is_not_available_before_it_was_performed(self):
        p = profile('HPS',self.annual('HPS'),'Technologie','2026-10-25')
        self.assertEqual(p['status'],'declared_to_review')
        self.assertFalse(p['policies'])

    def test_a_contradictory_basis_is_local_and_not_converted(self):
        f = self.annual('ADI'); f['accounting_basis']='consolidé IFRS'; before=deepcopy(f)
        p = profile('ADI',f,'Immobilier','2026-10-26')
        self.assertEqual(p['status'],'document_conflict')
        self.assertEqual(f,before); self.assertFalse(p['policies'])

    def test_published_choices_correct_the_supplied_generalizations(self):
        profiles = {s:profile(s,self.annual(s),'','2026-10-26') for s in
                    ('ADI','RDS','HPS','WAF','ATL','ARD','TGCC','EQD','SLM')}
        self.assertEqual(profiles['ADI']['framework'],'moroccan')
        self.assertEqual(profiles['TGCC']['framework'],'moroccan')
        self.assertEqual(profiles['ATL']['framework'],'moroccan')
        self.assertEqual(profiles['RDS']['framework'],'ifrs')
        self.assertIn('comptabilisés en charges',profiles['HPS']['policies'][0]['text'])
        self.assertIn('143,7',profiles['HPS']['policies'][0]['text'])
        self.assertIn('IFRS 4 et IAS 39',profiles['WAF']['policies'][0]['text'])
        self.assertIn('coût jusqu’à achèvement',profiles['ARD']['policies'][0]['text'])
        self.assertEqual(profiles['RDS']['comparability']['status'],'restated_comparative')
        self.assertEqual(profiles['SLM']['scope'],'social')

    def test_semester_keeps_its_own_declaration(self):
        f=self.annual('ADI');f['latest_report']={'period_end':'2026-06-30',
            'accounting_basis':'Consolidé IFRS', 'document_url':'https://www.ammc.ma/semester.pdf'}
        p=profile('ADI',f,'Immobilier','2026-10-26')
        self.assertEqual(p['framework'],'moroccan')
        self.assertEqual(p['latest_publication'],f['latest_report'])

    def test_invalid_or_unreviewed_evidence_cannot_be_promoted(self):
        for change in ('host','hash','page','review','topic_page','comparability_page'):
            data=deepcopy(catalog())
            if change=='host':data['sources']['HPS']['url']='https://example.org/account.pdf'
            if change=='hash':data['sources']['HPS']['sha256']='wrong'
            if change=='page':data['issuers']['HPS']['basis_page']=1
            if change=='review':data['sources']['HPS']['review_kind']='automatic_extraction'
            if change=='topic_page':data['topics']['research']['sources'][1]['page']=1
            if change=='comparability_page':data['issuers']['ADI']['comparability']['page']=1
            with self.assertRaises(ValueError):validate_catalog(data)

    def test_accounting_metadata_does_not_change_any_canonical_calculation(self):
        fixture=json.loads((ROOT/'data/market_snapshot.json').read_text())
        facts=json.loads((ROOT/'data/facts_reference.json').read_text())['records']
        asof=max(str(fixture['snapshot_updated'])[:10],date.today().isoformat())
        before=deepcopy(fixture); original=deepcopy(facts)
        with patch('nour.engine.accounting_profile',return_value={}):
            baseline=build_report(fixture,asof,facts=facts)
        enriched=build_report(fixture,asof,facts=facts)
        for old,new in zip(baseline['results'],enriched['results']):
            self.assertEqual(old['symbol'],new['symbol'])
            for key in ('fundamental','technical','canonical_score','historical_statistics','sector_indicators'):
                self.assertEqual(old[key],new[key],new['symbol']+' '+key)
        self.assertEqual(fixture,before);self.assertEqual(facts,original)

    def test_model_receives_sourced_rules_and_profile_via_existing_selector(self):
        report=json.loads((ROOT/'web/report.json').read_text())
        data=build_data(report)
        # Controlled profile so this selector test does not depend on live report years.
        data['symbols']['HPS']['accounting_profile']=profile('HPS',self.annual('HPS'),'','2026-10-26')
        context=context_for(data,['HPS'],'Quelles méthodes comptables HPS en 2025 ?')
        self.assertIn('accounting_research',context['definitions'])
        self.assertIn('comptabilisés en charges',context['selected']['HPS']['accounting_profile']['policies'][0]['text'])
        self.assertIn('https://www.ammc.ma/',context['definitions']['accounting_research'])
        self.assertNotIn('technical',context['selected']['HPS'])
        per_context=context_for(data,['HPS'],'Quel est son PER ?')
        self.assertIn('accounting_profile',per_context['selected']['HPS'])
        overview=context_for(data,['HPS'],'Synthèse complète HPS et normes comptables')
        self.assertIn('accounting_profile',overview['selected']['HPS'])
        self.assertIn('accounting_general',overview['definitions'])

    def test_learning_protocol_is_shared_by_agent_entry_points(self):
        for name in ('AGENTS.md','CLAUDE.md','.ecc/memory/project.md'):
            self.assertIn('docs/agent-learning.md',(ROOT/name).read_text())
        self.assertTrue((ROOT/'docs/agent-learning.md').exists())


if __name__ == '__main__':
    unittest.main()
