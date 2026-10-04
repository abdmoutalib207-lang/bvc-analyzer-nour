import copy
import json
import math
import unittest
from pathlib import Path
from nour.fundamentals import calculate
from nour.news import merge_news
from nour.report_contracts import synchronize_market
from nour.statistics import describe

ROOT=Path(__file__).resolve().parents[1]


class NewContracts(unittest.TestCase):
    def facts(self):
        return dict(url='https://www.ammc.ma/example.pdf',exercice=2025,faits={
            'resultat_net_part_groupe':dict(valeur=1.234567,page=1),
            'capitaux_propres_part_groupe':dict(valeur=10,page=2),
            'nombre_actions_au_rapport':dict(valeur=100000,page=2,unite='actions')})

    def test_full_precision_ratios_and_weighted_vs_existing_shares(self):
        f=self.facts();f['faits']['nombre_actions_retenu_pour_le_bpa']=dict(valeur=90000,page=3)
        f['faits']['nombre_actions_existant']=dict(valeur=110000,page=4)
        r=calculate({'price':100},f)
        self.assertEqual(r['eps_mad'],13.72)
        self.assertEqual(r['pe'],round(100/(1.234567e6/90000),2))
        self.assertEqual(r['pb'],round(100/(10e6/110000),2))
        self.assertEqual(r['roe_pct'],12.35)

    def test_currency_bool_nonfinite_and_page_guards(self):
        f=self.facts();f['devise']='TND'
        r=calculate({'price':100},f)
        self.assertIsNone(r['pe']);self.assertIsNone(r['roe_pct'])
        for bad in (True,float('nan'),float('inf')):
            f=self.facts();f['faits']['resultat_net_part_groupe']['valeur']=bad
            self.assertIsNone(calculate({'price':100},f)['eps_mad'])
        f=self.facts();f['faits']['resultat_net_part_groupe']['page']=0
        self.assertIsNone(calculate({'price':100},f)['eps_mad'])

    def test_no_minority_or_unresolved_capital_substitution(self):
        f=self.facts();f['capital_change_unresolved']=True
        r=calculate({'price':100},f)
        self.assertIsNone(r['eps_mad']);self.assertIsNone(r['pb'])
        self.assertIsNotNone(r['roe_pct'])
        f=self.facts();del f['faits']['capitaux_propres_part_groupe']
        f['faits']['capitaux_propres_consolides']=dict(valeur=12,page=2)
        self.assertIsNone(calculate({'price':100},f)['pb'])

    def test_semester_is_display_only_never_doubled_into_annual_ratios(self):
        f=self.facts();before=calculate({'price':100},f)
        f['latest_report']=dict(period_end='2026-06-30',reported_net_millions=999)
        after=calculate({'price':100},f)
        for key in ('eps_mad','pe','pb','roe_pct'):
            self.assertEqual(before[key],after[key])

    def test_no_false_ticker_association_and_official_resolution(self):
        symbols=['MNG','IBM','SRM','ADI','SNA','STK']
        def news(title,**kwargs):
            return dict(title=title,url='https://example.org/news',date='2026-10-02',
                        tickers=['MNG','IBM','SRM'],**kwargs)
        for title in ('NARSA sécurité routière','IBM et IA au travail','SRM : sociétés régionales multiservices'):
            self.assertEqual(merge_news([], [news(title)],symbols)['articles'][0]['tickers'],[])
        a=news('Résultats financiers Alliances');a.update(url='https://www.ammc.ma/sites/default/files/ADI_S1_26.pdf',validation_status='listed_officially')
        r=merge_news([], [a],symbols)['articles'][0]
        self.assertEqual(r['tickers'],['ADI']);self.assertFalse(r['usable_for_score'])
        a['title']='Résultats Sonasid';a['url']='https://www.ammc.ma/Sonasid.pdf'
        self.assertEqual(merge_news([], [a],symbols)['articles'][0]['tickers'],['SNA'])

    def test_market_blocks_share_one_date_and_missing_is_explicit(self):
        original={'market':{'last_session':'2026-09-25','masi':{'value':17818}}}
        r=synchronize_market(copy.deepcopy(original),dict(asof='2026-10-02',status='closed',masi={'value':17303}))
        self.assertEqual(r['market']['masi'],r['market_overview']['masi'])
        self.assertEqual(r['market_archive'],original['market'])
        self.assertEqual(synchronize_market({}, {})['market']['status'],'unavailable')

    def test_empirical_nonoverlapping_counts_and_wilson_not_forecast(self):
        bars=[dict(d=f'session-{i}',c=100+i,l=99+i,h=101+i) for i in range(601)]
        result=describe({'candles':bars})
        self.assertEqual([x['observations'] for x in result['horizons']],[600,120,30])
        for h in result['horizons']:
            self.assertEqual(h['positive_frequency_pct'],100)
            self.assertLess(h['wilson95_pct'][0],100)
            self.assertAlmostEqual(h['wilson95_pct'][1],100)
        resumed=describe({'candles':bars,'resumed_recently':True,'sessions_since_resume':12})
        self.assertTrue(all(h['state']=='insufficient' for h in resumed['horizons']))
        self.assertIn('Ni prévision',result['note'])

    def test_pinned_import_and_explicit_pending_coverage(self):
        f=json.loads((ROOT/'data/facts_reference.json').read_text())['records']
        self.assertEqual(sum(bool(r.get('url')) for r in f.values()),66)
        self.assertEqual(sum(bool(r.get('latest_report')) for r in f.values()),68)
        self.assertTrue(all(r['provenance'].get('repository')=='abdmoutalib207-lang/-bvc-analyzer'
                            or r['provenance'].get('source_type')=='regulator_pdf' for r in f.values()))
        self.assertIsNone(calculate({'price':48.65},f['ENK'])['eps_mad'])
        self.assertIsNone(calculate({'price':220},f['T2S'])['pe'])
        self.assertEqual(calculate({'price':6591},f['SMI'])['eps_mad'],241.39)
        self.assertEqual(f['RIS']['latest_report']['reported_net_millions'],144)
        self.assertEqual(f['RIS']['latest_report']['reported_net_including_exceptionals_millions'],313)

    def test_primary_annual_additions_and_financial_sector_separation(self):
        f=json.loads((ROOT/'data/facts_reference.json').read_text())['records']
        agm=calculate({'price':6000},f['AGM'])
        self.assertEqual(agm['roe_pct'],46.24)
        self.assertIsNone(agm['eps_mad'])
        slm=calculate({'price':500},f['SLM'])
        self.assertEqual(slm['eps_mad'],30.77)
        self.assertEqual(slm['book_value_per_share_mad'],round(870.833e6/3124119,2))
        self.assertEqual(slm['pnb_growth_pct'],1.42)
        self.assertIsNone(slm['revenue_growth_pct'])
        self.assertIsNone(slm['net_debt_ebitda'])
        eqd=calculate({'price':1000},f['EQD'])
        self.assertEqual(eqd['eps_mad'],59.01)
        self.assertIsNone(eqd['pb']);self.assertIsNone(eqd['roe_pct'])
        self.assertEqual(eqd['pnb_growth_pct'],9.41)
        self.assertEqual(eqd['evidence']['resultat_net_part_groupe']['page'],59)
        self.assertTrue(all(x['latest_report']['provenance']['repository']=='abdmoutalib207-lang/-bvc-analyzer'
                            for x in (f['AGM'],f['SLM'],f['EQD'])))


if __name__=='__main__': unittest.main()
