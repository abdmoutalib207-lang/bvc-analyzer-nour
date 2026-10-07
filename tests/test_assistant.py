import copy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nour.assistant import build_data, context_for, panel, source_links, read_briefings, read_history_files
from nour.assistant_server import AssistantError, Gateway, Provider, handler_for

ROOT = Path(__file__).resolve().parents[1]


class FakeProvider:
    enabled = True
    label = 'fake-for-test'

    def __init__(self):
        self.calls = []

    def complete(self, question, context):
        self.calls.append((question, context))
        return 'Explication de test, sans fournisseur réel.'


class AssistantFacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT/'web/report.json').read_text())

    def test_export_is_a_copy_without_score_or_fundamental_recalculation(self):
        original = copy.deepcopy(self.report)
        data = build_data(self.report)
        self.assertEqual(self.report, original)
        self.assertEqual(len(data['symbols']), 80)
        for row in self.report['results']:
            actual = data['symbols'][row['symbol']]
            self.assertEqual(actual['canonical_score'], row['canonical_score'])
            self.assertEqual(actual['historical_statistics'], row['historical_statistics'])
            for key in ('pe','eps_mad','roe_pct','latest_report','eps_denominator','net_debt_method'):
                self.assertEqual(actual['fundamental'][key], row['fundamental'].get(key))
            for key in ('day_turnover_mad_actual','day_shares','close_dates_last_60','close_series_last_60'):
                self.assertEqual(actual[key],row.get(key))
        self.assertEqual(data['market_volume_audit'],self.report.get('market_volume_audit'))
        self.assertEqual(data['runtime'],self.report.get('runtime'))
        data['symbols']['JET']['canonical_score']['value'] = -99
        self.assertEqual(self.report, original)

    def test_no_legacy_signal_or_arbitrary_private_field_is_exported(self):
        report = copy.deepcopy(self.report)
        report['private_key'] = 'must-not-escape'
        report['results'][0]['private_comment'] = 'must-not-escape'
        self.assertNotIn('must-not-escape', json.dumps(build_data(report)))
        self.assertNotIn('legacy_comparison', json.dumps(build_data(report)))

    def test_nonfinite_numbers_and_future_index_dates_do_not_escape(self):
        report = copy.deepcopy(self.report)
        report['masi_history']['2999-01-01'] = 10000
        report['results'][0]['price'] = float('nan')
        data = build_data(report)
        self.assertNotIn('2999-01-01', data['masi_history'])
        self.assertIsNone(data['symbols'][report['results'][0]['symbol']]['price'])
        json.dumps(data, allow_nan=False)

    def test_context_whitelists_symbols_and_does_not_use_facts_from_client(self):
        data = build_data(self.report)
        context = context_for(data, ['JET','MASI'], 'Que valait le MASI le 2026-03-11 ?')
        self.assertEqual(context['masi_dates']['2026-03-11'], data['masi_history']['2026-03-11'])
        self.assertNotIn('macro', context)
        for symbols in ([], ['UNKNOWN'], ['JET']*3, None, [['JET']]):
            with self.assertRaises((ValueError,TypeError)):
                context_for(data, symbols, 'question')

    def test_sources_reject_executable_or_relative_external_document_urls(self):
        data = build_data(self.report)
        data['symbols']['JET']['fundamental']['document_url'] = 'javascript:alert(1)'
        context = context_for(data,['JET'],'question')
        sources = source_links(context)
        self.assertTrue(any(s['url']=='titres/JET.html' for s in sources))
        self.assertFalse(any('javascript:' in s['url'] for s in sources))

    def test_panel_has_labelled_dialog_local_mode_and_no_key_input(self):
        text = panel('../')
        for needle in ('aria-labelledby="assistant-title"','data-prefix="../"',
                       'sans IA générative','maxlength="1200"','id="assistant-ai-option"'):
            self.assertIn(needle,text)
        self.assertNotIn('type="password"',text)

    def test_extended_facts_are_independent_copies_of_existing_results(self):
        original = copy.deepcopy(self.report)
        data = build_data(self.report)
        for key in ('research','intraday','score_archive'):
            self.assertEqual(data[key], self.report[key])
        for row in self.report['results']:
            for key in ('liquidity','trend','market_risk','sector_comparison','quality'):
                self.assertEqual(data['symbols'][row['symbol']][key],row.get(key))
        data['research']['rows'].clear()
        self.assertEqual(self.report,original)
        self.assertEqual(len(data['knowledge']['capabilities']),16)

    def test_news_export_omits_private_fields_undated_and_future_items(self):
        report=copy.deepcopy(self.report)
        report['news']=[{'title':'visible','published_at':report['analysis_date']+'T10:00:00Z',
                         'private_note':'must-not-escape'},
                        {'title':'future','published_at':'2999-01-01T00:00:00Z'},
                        {'title':'undated'}]
        news=build_data(report)['news']
        self.assertEqual([a['title'] for a in news],['visible'])
        self.assertNotIn('must-not-escape',json.dumps(news))

    def test_generated_briefings_and_history_manifest_are_dated_and_bounded(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'briefing.json').write_text(json.dumps({'generated_for':'2026-10-07','title':'visible','private_note':'hidden'}))
            (root/'cloture.json').write_text(json.dumps({'generated_for':'2999-01-01','title':'future'}))
            editions=read_briefings(root,'2026-10-07')
            self.assertEqual(list(editions),['briefing'])
            self.assertNotIn('private_note',editions['briefing'])
            (root/'historique').mkdir()
            raw='données exactes\n'.encode()
            (root/'historique'/'ADI.csv').write_bytes(raw)
            manifest=read_history_files(root,['ADI','../private','ZZZ'])
            self.assertEqual(manifest,{'ADI':{'url':'historique/ADI.csv','sha256':hashlib.sha256(raw).hexdigest()}})


class AssistantGateway(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = Path(self.tmp.name)
        self.data = build_data(json.loads((ROOT/'web/report.json').read_text()))
        (self.web/'assistant-data.json').write_text(json.dumps(self.data))
        self.provider = FakeProvider()
        self.gateway = Gateway(self.web,self.provider)

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_consent_and_verified_symbol_before_any_provider_call(self):
        for payload in ({'question':'bonjour','symbols':['JET']},
                        {'question':'x'*1201,'symbols':['JET'],'consent':True},
                        {'question':'bonjour','symbols':['UNKNOWN'],'consent':True},
                        {'question':'bonjour','symbols':[['JET']],'consent':True},
                        []):
            with self.assertRaises(AssistantError):
                self.gateway.answer(payload)
        self.assertEqual(self.provider.calls,[])

    def test_server_facts_override_fake_client_context(self):
        reply = self.gateway.answer({'question':'explique','symbols':['JET'],'consent':True,
                                     'context':{'price':999999},'model':'evil','url':'http://evil'})
        self.assertEqual(reply['mode'],'llm')
        context = self.provider.calls[0][1]
        self.assertEqual(context['selected']['JET']['price'],self.data['symbols']['JET']['price'])
        self.assertNotIn('evil',json.dumps(context))

    def test_budget_and_missing_data_do_not_silently_fall_back(self):
        self.gateway.minute_limit = 1
        payload={'question':'explique','symbols':['JET'],'consent':True}
        self.gateway.answer(payload)
        with self.assertRaises(AssistantError) as caught:
            self.gateway.answer(payload)
        self.assertEqual(caught.exception.status,429)
        self.assertEqual(len(self.provider.calls),1)
        (self.web/'assistant-data.json').unlink()
        with self.assertRaises(AssistantError) as caught:
            self.gateway.answer(payload)
        self.assertEqual(caught.exception.status,503)
        self.assertEqual(len(self.provider.calls),1)

    def test_provider_requires_explicit_model_https_and_server_secret(self):
        self.assertFalse(Provider({}).enabled)
        self.assertTrue(Provider({'NOUR_LLM_BASE_URL':'http://localhost:11434/v1','NOUR_LLM_MODEL':'local-model'}).enabled)
        for base,key in [('http://evil.test/v1','secret'),('https://user:pass@evil.test/v1','secret'),
                         ('https://evil.test/v1?key=bad','secret'),('https://evil.test/v1','')]:
            with self.assertRaises(ValueError):
                Provider({'NOUR_LLM_BASE_URL':base,'NOUR_LLM_MODEL':'model','NOUR_LLM_API_KEY':key})

    def test_provider_errors_do_not_leak_secrets_or_claim_a_response(self):
        provider=Provider({'NOUR_LLM_BASE_URL':'https://provider.test/v1',
                          'NOUR_LLM_MODEL':'model','NOUR_LLM_API_KEY':'private-test-value'})
        with patch('nour.assistant_server.build_opener') as mock:
            mock.return_value.open.side_effect=URLError('private-test-value')
            with self.assertRaises(AssistantError) as caught:
                provider.complete('question',{})
        self.assertEqual(caught.exception.status,502)
        self.assertNotIn('private-test-value',str(caught.exception))

    def test_http_rejects_cross_origin_dns_rebinding_and_missing_consent(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.gateway))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base+'/assistant-config.json') as res:
                config=json.load(res)
            self.assertEqual(config['endpoint'],'/api/assistant')
            self.assertNotIn('API_KEY',json.dumps(config))
            payload=json.dumps({'question':'explique','symbols':['JET'],'consent':True}).encode()
            for headers in ({'Origin':'https://evil.test'}, {'Host':'evil.test','Origin':'http://evil.test'}, {}):
                request=Request(base+'/api/assistant',data=payload,
                    headers={'Content-Type':'application/json',**headers})
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request)
                self.assertEqual(caught.exception.code,403)
            request=Request(base+'/api/assistant',data=payload,
                            headers={'Content-Type':'application/json','Origin':base})
            with urlopen(request) as res:
                self.assertEqual(json.load(res)['mode'],'llm')
            self.assertEqual(len(self.provider.calls),1)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
