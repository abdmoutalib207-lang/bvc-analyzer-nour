"""Audit regressions: compact retrieval, no hidden reservations, publication truth."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from nour.assistant import build_data, source_links
from nour.assistant_context import compact_data, retrieve
from nour.market import import_session, CASABLANCA
from nour.publication import collection_view, history_readiness, publication_manifest
from nour.site import collection_panel, provenance_panel

ROOT = Path(__file__).resolve().parents[1]


class Consolidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_data(json.loads((ROOT/'web/report.json').read_text()))
        cls.index = compact_data(cls.data)

    def test_every_title_summary_fits_without_series_or_removed_warnings(self):
        before = copy.deepcopy(self.index)
        for symbol, row in self.data['symbols'].items():
            context = retrieve(self.index, [symbol], 'Synthèse complète : marché, technique, fondamentaux, risques, sources')
            selected = context['selected'][symbol]
            self.assertEqual(selected['fundamental']['warnings'], row['fundamental']['warnings'])
            self.assertEqual(selected['fundamental']['evidence'], row['fundamental']['evidence'])
            self.assertNotIn('close_series_last_60', selected)
            self.assertNotIn('research', context)
            self.assertLessEqual(len(json.dumps(context, ensure_ascii=False, separators=(',', ':')).encode()), 40000)
        self.assertEqual(self.index, before)

    def test_intent_routing_avoids_wrong_domains_and_uses_canonical_values(self):
        context = retrieve(self.index, ['ADI'], 'Explique ses fondamentaux et son PER')
        self.assertEqual(context['intents'], ['fundamentals'])
        self.assertNotIn('macro', context)
        self.assertNotIn('technical', context['selected']['ADI'])
        self.assertEqual(context['selected']['ADI']['fundamental']['pe'], self.data['symbols']['ADI']['fundamental']['pe'])
        self.assertTrue(any('exceptionnels' in rule and 'normalisé' in rule for rule in context['rules']))
        self.assertEqual(retrieve(self.index, ['ADI', 'ATW'], 'Compare ADI et ATW')['intents'], ['sector'])

    def test_intraday_title_context_excludes_other_quotes_and_keeps_all_reservations(self):
        index=copy.deepcopy(self.index)
        index['intraday']={'status':'provisional','observed_at':'2026-10-19T09:55:00Z','notice':'Observations provisoires non définitives',
            'quotes':{s:{'price':row.get('price'),'asof':'2026-10-19','shares':100,'turnover_mad':1000,'notice':'Aucune clôture confirmée'} for s,row in index['symbols'].items()}}
        index['error_memory_summary']={'lessons':1,'lessons_catalog':[{'title':'Règle conservée','rule':'Ne pas inventer un chiffre'}],'url':'error-memory.json'}
        before=copy.deepcopy(index)
        for symbol in index['symbols']:
            context=retrieve(index,[symbol],'Synthèse complète : marché, technique, fondamentaux, risques, sources')
            self.assertEqual(list(context['intraday']['quotes']),[symbol])
            self.assertEqual(context['intraday']['quote_count'],len(index['symbols']))
            self.assertEqual(context['intraday']['notice'],index['intraday']['notice'])
            self.assertEqual(context['selected'][symbol]['fundamental']['warnings'],index['symbols'][symbol]['fundamental']['warnings'])
            self.assertEqual(context['selected'][symbol]['fundamental']['evidence'],index['symbols'][symbol]['fundamental']['evidence'])
            self.assertNotIn('lessons_catalog',context['error_memory_summary'])
        self.assertEqual(index,before)
        cases=[(['ADI'],'Synthèse complète ADI'),(['MASI'],'Qualité du marché'),(['ADI'],'Journal des erreurs et qualité')]
        self.assertEqual(retrieve(index,['ADI'],cases[-1][1])['error_memory_summary']['lessons_catalog'],index['error_memory_summary']['lessons_catalog'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'intraday.json'
            path.write_text(json.dumps({'index':index,'cases':[{'symbols':s,'question':q,'expected':retrieve(index,s,q)} for s,q in cases]},ensure_ascii=False))
            subprocess.run(['node','tools/compare_context.mjs',str(path)],cwd=ROOT,check=True,capture_output=True)

    def test_pdf_pages_and_blocked_debt_remain_available(self):
        context = retrieve(self.index, ['ADI'], 'Pourquoi la dette nette est suspendue ?')
        f = context['selected']['ADI']['fundamental']
        self.assertIsNone(f['net_debt_strict_mmad'])
        self.assertEqual(f['debt_reconciliation']['status'], 'unresolved')
        urls = {s['url'] for s in source_links(context)}
        for page in (21, 22, 50):
            self.assertIn(f['document_url']+f'#page={page}', urls)

    def test_oversized_evidence_fails_explicitly_without_trimming(self):
        index = copy.deepcopy(self.index)
        index['symbols']['ADI']['fundamental']['warnings'] = ['Réserve importante ' * 10000]
        with self.assertRaisesRegex(ValueError, 'preuves requises'):
            retrieve(index, ['ADI'], 'PER ADI')

    def test_python_and_worker_context_are_identical(self):
        cases = [(['ADI'], 'PER ADI'), (['ADI'], 'Quel RSI ?'),
                 (['ATW'], 'Synthèse complète de cette banque et ses fondamentaux'),
                 (['ADI','RDS'], 'Compare ces titres'), (['MASI'], 'MASI au 2026-03-31'),
                 (['MASI'], 'Brent et actualités macro'), (['ADI'], 'Résume le briefing'),
                 (['ADI'], 'Quel RSI au 31/03/26 ?'),
                 (['HPS'], 'HPS active-t-il sa R&D en 2025 ?'),
                 (['ADI','RDS'], 'Normes comptables ADI RDS et PCSI 2025'),
                 (['WAF'], 'IFRS 17 Wafa Assurance en 2025'),
                 (['EQD'], 'EQDOM en IFRS 9 automatiquement ?')]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'cases.json'
            path.write_text(json.dumps({'index':self.index,'cases':[
                {'symbols':symbols, 'question':question, 'expected':retrieve(self.index,symbols,question)}
                for symbols,question in cases]}, ensure_ascii=False))
            subprocess.run(['node','tools/compare_context.mjs',str(path)],cwd=ROOT,check=True,capture_output=True)

    def test_dated_questions_never_substitute_current_indicators_or_invalid_dates(self):
        context=retrieve(self.index,['ADI'],'Quel était le PER au 31/03/26 ?')
        self.assertNotIn('fundamental',context['selected']['ADI'])
        self.assertNotIn('price',context['selected']['ADI'])
        self.assertEqual(context['selected']['ADI']['requested_dates'],['2026-03-31'])
        with self.assertRaises(ValueError):retrieve(self.index,['ADI'],'RSI au 31/02/2026 ?')

    def test_published_average_rounding_is_stable_across_python_versions(self):
        from nour.analytics import technical
        # Reviewed CDM last 20 closes at 2026-10-16; literal independent fixture.
        closes=[955.0,980.0,960.0,960.0,945.0,943.0,950.0,960.0,939.9,930.0,
                930.0,929.0,940.0,921.0,930.0,922.0,921.5,921.5,921.0,914.4]
        record={'candles':[dict(o=c,h=c,l=c,c=c,v=1) for c in closes]}
        self.assertEqual(technical(record)['sma20'],938.67)

    def test_history_depth_is_separate_from_readiness_and_resume_boundary(self):
        for symbol in ('ADI','IBM','MDP','CMT','DIS'):
            row = self.data['symbols'][symbol]
            result = history_readiness(row)
            self.assertEqual(result['state'], row['decision'])
            self.assertEqual(result['last_close'], row['asof'])
        cmt = history_readiness(self.data['symbols']['CMT'])
        self.assertTrue(cmt['post_resume_only'])
        self.assertLess(cmt['indicator_sessions'], cmt['validated_close_sessions'])
        self.assertIn('post-reprise', cmt['label'])

    def test_historical_conflicts_are_visible_and_not_invented(self):
        health={'result':'conflict','details':{'conflicts':[{'symbol':'BOA','session':'2026-10-16','fields':['v']}]}}
        self.assertFalse(collection_view(health)['fully_validated'])
        text = collection_panel(health)
        for value in ('BOA','2026-10-16','Non archivée dans cet ancien relevé','refusée pour conflit'):
            self.assertIn(value, text)
        self.assertIn('Commit du générateur',provenance_panel({}))

    def test_new_conflicts_keep_both_values_without_mutating_history(self):
        fixture = json.loads((ROOT/'data/market_snapshot.json').read_text())
        codes = json.loads((ROOT/'data/source_codes.json').read_text())
        original = copy.deepcopy(fixture)
        bar = fixture['records']['ADI']['candles'][-1]
        quantity = int(bar['v'])+1
        row={'Symbol':codes['ADI'],'DateDernierCours':datetime.fromisoformat(bar['d']).strftime('%d/%m/%Y'),
             'Cours':bar['c'],'Ouverture':bar['o'],'PlusHaut':bar['h'],'PlusBas':bar['l'],
             'QteEchangee':quantity,'Volumes':bar['c']*quantity}
        # The publication snapshot advances; exercise a conflict after its own
        # session closes rather than freezing the clock before newer quotes.
        collected_at=datetime.fromisoformat(bar['d']).replace(hour=19,tzinfo=CASABLANCA)
        updated, details = import_session(fixture,[row],codes,collected_at,minimum=1)
        conflict=details['conflicts'][0]
        self.assertEqual(conflict['retained']['v'],bar['v'])
        self.assertEqual(conflict['observed']['v'],quantity)
        self.assertEqual(conflict['resolution'],'pending_review')
        self.assertEqual(updated['records']['ADI']['candles'],fixture['records']['ADI']['candles'])
        self.assertEqual(fixture,original)

    def test_publication_manifest_hashes_actual_files_and_never_claims_deployed(self):
        with tempfile.TemporaryDirectory() as tmp:
            web=Path(tmp)
            for name in ('report.json','assistant-data.json','assistant-context.json','runtime.json','index.html'):
                (web/name).write_text('{}')
            manifest=publication_manifest(web,'a'*40)
            self.assertEqual(manifest['publication_commit'],'a'*40)
            self.assertEqual(manifest['stage'],'artifact_prepared_for_deployment')
            self.assertEqual(manifest['sha256']['index.html'],hashlib.sha256(b'{}').hexdigest())
            with self.assertRaises(ValueError):publication_manifest(web,'main')


if __name__ == '__main__':
    unittest.main()
