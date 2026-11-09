import base64
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nour.screener_reconciliation import SOURCE_URL, collect, decode_script, reconcile
from tools.update_screener_reconciliation import main

NOW = '2026-11-09T15:30:00+01:00'


def fixtures():
    payload = dict(generated_at='2026-11-09T13:19', docs=['Rapport annuel 2025'],
                   fields={'RNPG':dict(unit='Mcur'), 'CA':dict(unit='Mcur'), 'dette_nette':dict(unit='Mcur'), 'EBE':dict(unit='Mcur')},
                   companies={'ADI':dict(ticker='ADI', name='Alliances', scope='consolidated', currency='MAD', regime='PCGI_2025',
                     regimes={'2025':'PCGI_2025','2026':'PCGI_2025'}, f={'FY2025':{'RNPG':{'reported':dict(v=407.601,d=0,p=22,l='Part du Groupe',m='text_parse')}},'H1-2026':{'RNPG':{'reported':dict(v=229.599,d=0,p=3,l='Part du Groupe',m='text_parse')}}})})
    fact=dict(valeur=407.601, unite='MMAD', devise='MAD', base='consolidé normes marocaines',
              period_end='2025-12-31', url='https://www.ammc.ma/ADI.pdf', page=22,
              document_hash='sha256:'+'a'*64, validation_status='selected_pages_visually_checked')
    nour=dict(records={'ADI':dict(exercice=2025, exercice_clos='2025-12-31', devise='MAD',
                   accounting_basis='consolidé normes marocaines', faits={'resultat_net_part_groupe':fact})})
    return payload, nour


def script(payload):
    encoded=base64.b64encode(gzip.compress(json.dumps(payload).encode())).decode()
    return ('irrelevantJavascript();atob("'+encoded+'");neverExecuteMe();').encode()


def row(report, key='resultat_net_part_groupe', period='FY2025'):
    return next(r for r in report['rows'] if r['nour_field']==key and r['period']==period)


class ScreenerReconciliationTests(unittest.TestCase):
    def test_real_data_contract_no_evaluation_and_immutable_facts(self):
        p,n=fixtures(); before=deepcopy((p,n))
        out=collect(n,now=NOW,source_codes={'ADI':'ADI'},script=script(p))
        self.assertEqual(out['status'],'collected')
        self.assertEqual(row(out)['status'],'agreement')
        self.assertFalse(out['automatic_corrections']);self.assertFalse(out['documents_certified'])
        self.assertFalse(out['source_timezone_attested'])
        self.assertRegex(out['nour_facts_sha256'],r'^sha256:[a-f0-9]{64}$')
        self.assertEqual((p,n),before)
        self.assertEqual(row(out)['screener_provenance']['provenance_grade'],'label_page_only')
        self.assertIsNone(row(out)['screener_provenance'].get('url'))

    def test_difference_and_rounding_are_distinct(self):
        p,n=fixtures(); own=n['records']['ADI']['faits']['resultat_net_part_groupe']
        own['valeur']=407.6014
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['status'],'rounding')
        own['valeur']=407.7
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['status'],'difference')

    def test_millions_are_not_mixed_with_thousands(self):
        p,n=fixtures();n['records']['ADI']['faits']['resultat_net_part_groupe']['unite']='KMAD'
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['reason'],'unit_missing_or_mismatch')

    def test_scopes_and_reporting_standards_never_blended(self):
        for field,value in [('scope','social'),('regime','IFRS')]:
            p,n=fixtures();p['companies']['ADI'][field]=value
            if field=='regime':p['companies']['ADI']['regimes']={}
            self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['status'],'not_comparable')

    def test_total_income_is_not_group_income_or_social_income(self):
        p,n=fixtures();f=n['records']['ADI']['faits'];f['resultat_net_consolide']=f.pop('resultat_net_part_groupe')
        out=reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'})
        self.assertEqual(row(out,'resultat_net_consolide')['status'],'missing')
        self.assertEqual(row(out)['status'],'missing')
        p,n=fixtures();f=n['records']['ADI']['faits'];f['resultat_net_social']=f.pop('resultat_net_part_groupe')
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}),'resultat_net_social')['reason'],'social_profit_is_not_group_profit')

    def test_losses_zero_boolean_absence_are_distinct(self):
        p,n=fixtures();f=n['records']['ADI']['faits']['resultat_net_part_groupe'];ext=p['companies']['ADI']['f']['FY2025']['RNPG']['reported']
        for value in (-10,0):
            f['valeur']=ext['v']=value
            self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['status'],'agreement')
        for value in (True,None):
            ext['v']=value
            self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['status'],'missing')

    def test_derived_debt_definitions_and_ebe_not_certified(self):
        p,n=fixtures();f=n['records']['ADI']['faits'];q=p['companies']['ADI']['f']['FY2025']
        for nk,sk in [('endettement_net','dette_nette'),('excedent_brut_exploitation','EBE')]:
            f[nk]=deepcopy(f['resultat_net_part_groupe']);q[sk]={'reported':dict(v=407.601,d=0,p=22,m='derived')}
        out=reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'})
        self.assertEqual(row(out,'endettement_net')['reason'],'definition_review_required')
        self.assertEqual(row(out,'excedent_brut_exploitation')['reason'],'derived_definition_review_required')

    def test_missing_reference_and_unverified_upstream_stay_noncomparable(self):
        p,n=fixtures();p['companies']['ADI']['f']['FY2025']['RNPG']['reported']['p']=None
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['reason'],'source_reference_incomplete')
        p['companies']['ADI']['unverified']=True
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['reason'],'upstream_unverified')

    def test_semester_is_separate_never_annualized(self):
        p,n=fixtures();n['records']['ADI']['latest_report']=dict(period_end='2026-06-30', currency='MAD',
           reported_net_millions=229.599, accounting_basis='résultat net part du groupe consolidé normes nationales',document_url='https://www.ammc.ma/S1.pdf')
        out=reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'})
        self.assertEqual(row(out,period='H1-2026')['screener_value'],229.599)
        self.assertEqual(row(out,period='H1-2026')['status'],'agreement')
        self.assertEqual(row(out)['nour_value'],407.601)
        self.assertFalse(any(r['period'].startswith('TTM') for r in out['rows']))
        n['records']['ADI']['latest_report']['accounting_basis']='consolidé normes nationales'
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}),period='H1-2026')['status'],'not_comparable')

    def test_future_source_and_invalid_clock_rejected(self):
        p,n=fixtures();p['generated_at']='2026-11-10T00:00'
        self.assertEqual(collect(n,now=NOW,source_codes={'ADI':'ADI'},script=script(p))['status'],'unavailable')
        with self.assertRaises(ValueError):reconcile(p,n,checked_at='2026-11-09T15:30')

    def test_restated_never_silently_selected_when_reported_missing(self):
        p,n=fixtures();v=p['companies']['ADI']['f']['FY2025']['RNPG'];v['restated']=v.pop('reported')
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['status'],'missing')

    def test_bad_gzip_ambiguous_payload_size_and_nonfinite_json_rejected(self):
        p,n=fixtures();good=script(p)
        for bad in (b'let x = 4;', b'atob("AAAA")',good+good):
            with self.assertRaises(Exception):decode_script(bad)
        with patch('nour.screener_reconciliation.MAX_JSON',100):
            with self.assertRaises(ValueError):decode_script(good)
        p['companies']['ADI']['f']['FY2025']['RNPG']['reported']['v']=float('inf')
        with self.assertRaises(ValueError):decode_script(script(p))

    def test_failed_refresh_preserves_dated_last_success_and_disagreements(self):
        p,n=fixtures();n['records']['ADI']['faits']['resultat_net_part_groupe']['valeur']=500
        previous=collect(n,now=NOW,source_codes={'ADI':'ADI'},script=script(p));before=deepcopy(previous)
        out=collect(n,previous,now='2026-11-10T15:30:00+01:00',source_codes={'ADI':'ADI'},script=b'bad')
        self.assertEqual(out['status'],'degraded')
        self.assertEqual(out['rows'],previous['rows']);self.assertEqual(out['last_success_at'],NOW)
        self.assertEqual(out['source_sha256'],previous['source_sha256'])
        self.assertEqual(previous,before)

    def test_network_fetch_has_fixed_origin_limit_and_rejects_redirect(self):
        p,n=fixtures();calls=[]
        def fetcher(url,origins,**kwargs):
            calls.append((url,origins,kwargs));return script(p),'https://elsewhere.invalid/file','application/javascript'
        self.assertEqual(collect(n,now=NOW,source_codes={'ADI':'ADI'},fetcher=fetcher)['status'],'unavailable')
        self.assertEqual(calls[0][0],SOURCE_URL);self.assertEqual(calls[0][2]['timeout'],20)
        self.assertEqual(calls[0][1],{'https://ms-screener.vercel.app'})

    def test_universe_absence_does_not_invent_financial_facts(self):
        p,n=fixtures();out=reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'},symbols=['ADI','DIS','IBM'])
        self.assertEqual(out['summary']['issuers'],3)
        self.assertEqual(out['summary']['nour_issuers'],1)
        self.assertEqual(out['summary']['compared_issuers'],1)
        self.assertEqual(len(out['coverage']),3)
        self.assertFalse(any(r['symbol']=='DIS' for r in out['rows']))

    def test_missing_period_cannot_be_inferred_from_annual_header(self):
        p,n=fixtures();n['records']['ADI']['faits']['resultat_net_part_groupe'].pop('period_end')
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}))['reason'],'nour_period_not_documented')

    def test_legal_share_count_does_not_require_financial_reporting_scope(self):
        p,n=fixtures();p['fields']['nb_titres']={'unit':'count'}
        p['companies']['ADI']['f']['FY2025']['nb_titres']={'reported':dict(v=22078588,d=0,p=50,m='text_parse')}
        n['records']['ADI']['faits']['nombre_actions']=dict(valeur=22078588,unite='actions',period_end='2025-12-31',page=50)
        self.assertEqual(row(reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'}),'nombre_actions')['status'],'agreement')

    def test_ticker_collision_sonasid_and_stokvis_use_the_registry_first(self):
        p,n=fixtures();prototype=p['companies'].pop('ADI');record=n['records'].pop('ADI')
        codes={'SNA':'SID','STK':'SNA'}
        for symbol,source,name,value in [('SNA','SID','Sonasid',900),('STK','SNA','Stokvis Nord Afrique',100)]:
            c=deepcopy(prototype);c.update(ticker=source,name=name);c['f']['FY2025']['RNPG']['reported']['v']=value
            p['companies'][source]=c;r=deepcopy(record);r['faits']['resultat_net_part_groupe']['valeur']=value;n['records'][symbol]=r
        out=reconcile(p,n,checked_at=NOW,source_codes=codes)
        self.assertEqual([r['status'] for r in out['rows']],['agreement','agreement'])
        self.assertEqual([(r['symbol'],r['screener_symbol'],r['screener_value']) for r in out['rows']],[('SNA','SID',900),('STK','SNA',100)])
        self.assertFalse(out['identity_provenance']['isin_verified'])

    def test_unmapped_duplicate_codes_and_renamed_issuer_require_review(self):
        p,n=fixtures();out=reconcile(p,n,checked_at=NOW,source_codes={})
        self.assertEqual(out['coverage'][0]['status'],'identity_unmapped');self.assertEqual(out['rows'],[])
        with self.assertRaises(ValueError):reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI','ADH':'ADI'},symbols=['ADI','ADH'])
        p['companies']['ADI']['name']='A different issuer'
        out=reconcile(p,n,checked_at=NOW,source_codes={'ADI':'ADI'})
        self.assertEqual(out['coverage'][0]['status'],'identity_review_required');self.assertEqual(out['rows'],[])

    def test_cli_offline_leaves_canonical_facts_untouched(self):
        p,n=fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir();(root/'web').mkdir()
            source=root/'app.js';source.write_bytes(script(p));(root/'data/source_codes.json').write_text(json.dumps({'ADI':'ADI'}));facts=root/'data/facts_reference.json';facts.write_text(json.dumps(n));before=facts.read_bytes()
            self.assertEqual(main(['--root',str(root),'--input',str(source),'--now',NOW]),0)
            self.assertEqual(facts.read_bytes(),before)
            self.assertEqual(json.loads((root/'data/screener_reconciliation.json').read_text()),json.loads((root/'web/screener-reconciliation.json').read_text()))


if __name__=='__main__':unittest.main()
