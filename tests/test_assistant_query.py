"""Universe retrieval and browser/Worker parity, grounded in published Nour facts."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from nour.assistant import build_data, read_briefings, source_links
from nour.assistant_context import compact_data, retrieve, ContextError
from nour.assistant_query import select

ROOT=Path(__file__).resolve().parents[1]


class AssistantQuery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report=json.loads((ROOT/'web/report.json').read_text())
        cls.data=build_data(report,read_briefings(ROOT/'web',report['analysis_date']))
        cls.index=compact_data(cls.data)

    def test_numeric_selection_matches_canonical_values_without_missing_zeroes(self):
        r=select(self.index,'Quelles valeurs ont un PER inférieur à 15 et un ROE supérieur à 10 % ?')
        expected=[s for s,x in self.data['symbols'].items() if isinstance(x['fundamental']['pe'],(int,float))
                  and x['fundamental']['pe']<15 and isinstance(x['fundamental']['roe_pct'],(int,float)) and x['fundamental']['roe_pct']>10]
        self.assertEqual(r['matched'],len(expected))
        self.assertEqual([row['symbol'] for row in r['rows']],sorted(expected)[:5])
        for row in r['rows']:
            canonical=self.data['symbols'][row['symbol']]['fundamental']
            self.assertEqual(row['values']['pe'],canonical['pe'])
            self.assertEqual(row['values']['roe'],canonical['roe_pct'])
            self.assertEqual(row['warnings'],canonical['warnings'])
            self.assertEqual(row['latest_report'],canonical['latest_report'])

    def test_blocked_and_missing_are_different(self):
        blocked=select(self.index,'Valeurs avec dette nette suspendue')
        expected={s for s,r in self.data['symbols'].items() if r['fundamental']['metric_availability']['net_debt_strict_mmad']['status']=='blocked'}
        self.assertEqual(blocked['matched'],len(expected))
        self.assertTrue(expected)
        self.assertNotIn('ATW',expected)
        for row in blocked['rows']:
            self.assertIsNone(row['values']['debt'])
            self.assertEqual(row['metric_availability']['net_debt_strict_mmad']['status'],'blocked')

    def test_rankings_preserve_exercise_and_sector_without_certifying_comparability(self):
        r=select(self.index,'Les 5 PER les plus faibles du secteur Banque en 2025')
        self.assertTrue(r['rows'])
        self.assertTrue(all(x['sector']=='Banque' and x['exercise']==2025 for x in r['rows']))
        self.assertIn('ne constitue pas une comparaison sectorielle validée',r['notice'])
        self.assertEqual([x['values']['pe'] for x in r['rows']],sorted(x['values']['pe'] for x in r['rows']))
        for q in ['Quelles valeurs ont un PER inférieur à 15 ou un ROE supérieur à 10 ?',
                  'Quelles valeurs ont un PER inférieur à 15 et un ESG supérieur à 80 ?',
                  'Les 5 RSI les plus faibles en 2025','Les 5 PER les plus faibles S1 2026',
                  'Les 5 PER les plus faibles du secteur inconnu']:
            result=select(self.index,q)
            self.assertTrue(result['error'],q)
            self.assertFalse(result['rows'])

    def test_context_paginates_whole_title_proofs_without_shortening_warnings(self):
        r=retrieve(self.index,['MASI'],'Les 20 PER les plus faibles en 2025')
        selected=r['query_result']
        self.assertGreater(selected['omitted_for_context_budget'],0)
        self.assertLessEqual(len(json.dumps(r,ensure_ascii=False,separators=(',',':')).encode()),40000)
        for row in selected['rows']:
            self.assertEqual(row['warnings'],self.data['symbols'][row['symbol']]['fundamental']['warnings'])
        bad=copy.deepcopy(self.index)
        for row in bad['symbols'].values():
            row['fundamental']['warnings']=['Avertissement documentaire '*5000]
        with self.assertRaises(ContextError):
            retrieve(bad,['MASI'],'Les 5 PER les plus faibles en 2025')

    def test_briefing_selection_contains_real_editorial_and_requested_title_only(self):
        before=copy.deepcopy(self.index)
        result=retrieve(self.index,['ADI'],'Résume le briefing de clôture')
        b=result['briefings']['cloture']
        self.assertEqual(b['editorial'],self.data['briefings']['cloture']['editorial'])
        self.assertTrue(all(f['symbol']=='ADI' for f in b['focus']))
        self.assertTrue(b['focus'][0]['reading']['paragraphs'])
        self.assertNotIn('fundamental',b['focus'][0]['reading'])
        self.assertEqual(self.index,before)
        dated=retrieve(self.index,['ADI'],'Briefing de clôture le 01/01/2023')
        self.assertEqual(dated['briefings'],{})

    def test_dated_mixed_news_does_not_expose_current_ratio_as_historical(self):
        r=retrieve(self.index,['ADI'],'PER et actualités au 31/03/2026')
        self.assertNotIn('fundamental',r['selected']['ADI'])
        self.assertNotIn('price',r['selected']['ADI'])
        self.assertEqual(r['selected']['ADI']['requested_dates'],['2026-03-31'])
        self.assertIn('news',r)

    def test_ranked_source_links_have_provided_document_pages(self):
        r=retrieve(self.index,['MASI'],'Les 5 PER les plus faibles en 2025')
        urls={s['url'] for s in source_links(r)}
        for row in r['query_result']['rows']:
            self.assertIn(row['url'],urls)
            for e in row['evidence'].values():
                if isinstance(e.get('page'),int) and e['page']>0:
                    self.assertIn((e.get('document_url') or row['document_url'])+f"#page={e['page']}",urls)

    def test_python_worker_and_browser_query_contracts_agree(self):
        queries=['Les 5 PER les plus faibles en 2025','Les 20 PER les plus faibles en 2025',
                 'Quelles sont les valeurs qui ont un PER inférieur à 15 et un ROE supérieur à 10 % ?',
                 'Montre les sociétés ayant un PER inférieur à 15 et un ROE supérieur à 10 %',
                 'Quelles valeurs ont le ROE le plus élevé ?',
                 'Quelles sont les meilleures valeurs avec un PER ?',
                 'Classement PER décroissant','Classement PER croissant',
                 'Quelles valeurs ont une dette nette inférieure à 100 MAD ?',
                 'Quelles valeurs ont une dette nette inférieure à 100 MMAD ?',
                 'Quelles valeurs ont une dette nette inférieure à 1 000 MMAD ?',
                 'Quelles valeurs ont un PER inférieur à 1e3 ?',
                 'Quelles valeurs ont un PER entre 10 et 20 ?',
                 'Quelles valeurs ont un cours sous la MM20 ?',
                 'Quelles valeurs ont un PER inférieur à 15 et un ROE supérieur à 10 % ?',
                 'Les 5 PER les plus faibles du secteur Banque en 2025','Valeurs avec dette nette suspendue',
                 'Quelles valeurs ont un PER >= 15 et un ROE <= 10 ?',
                 'Quelles valeurs ont un MACD supérieur à 0 ?',
                 'Quelles valeurs ont un PER inférieur à 15 ou un ROE supérieur à 10 ?',
                 'Les 5 RSI les plus faibles en 2025','Résume le briefing de clôture',
                 'Briefing de clôture le 01/01/2023','PER et actualités au 31/03/2026']
        cases=[{'symbols':['MASI'],'question':q,'expected':retrieve(self.index,['MASI'],q)} for q in queries]
        cases.append({'symbols':['ADI'],'question':'Résume le briefing de clôture','expected':retrieve(self.index,['ADI'],'Résume le briefing de clôture')})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queries.json'
            path.write_text(json.dumps({'index':self.index,'cases':cases},ensure_ascii=False))
            result=subprocess.run(['node','tools/compare_context.mjs',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
