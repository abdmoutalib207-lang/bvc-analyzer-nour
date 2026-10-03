import copy
import unittest
from nour.editorial import comparison, market_reading, title_reading
from nour.briefing import create_briefing
from nour.briefing_view import render_editorial, briefing_text


def row(symbol='ADI'):
    return {'symbol':symbol,'name':'Issuer','asof':'2026-10-02','price':90,'decision':'OBSERVABLE',
            'technical':{'support20':95,'resistance20':120,'sma20':102,'sma50':106,'rsi14':24,
                         'volume_vs_median20':3,'limited_by_resumption':False},
            'fundamental':{},'liquidity':{},'canonical_score':{'value':20,'state':'CALCULABLE'},
            'quality':{'issues':[]},'close_series_last_60':[100,90],
            'close_dates_last_60':['2026-10-01','2026-10-02'],'day_turnover_mad_actual':1e6}


def report():
    dates={f'2026-09-{n:02}':105-n/10 for n in range(10,31)}
    dates['2026-10-01']=100
    return {'analysis_date':'2026-10-03','snapshot_updated':'2026-10-03','market':{},
            'results':[row()], 'masi_history':dates,
            'market_overview':{'asof':'2026-10-02','status':'closed',
                'masi':{'asof':'2026-10-02','value':90,'change_pct':-10},
                'breadth':{'up':1,'down':8,'flat':1,'quoted':10},
                'turnover_mad':2e6,'high':105,'low':89,'sectors':[]},'news':[]}


class EditorialContracts(unittest.TestCase):
    def test_relative_performance_requires_same_two_sessions(self):
        r=row()
        self.assertEqual(comparison(r,'2026-10-02','2026-10-01'),-10)
        self.assertIsNone(comparison(r,'2026-10-02','2026-09-30'))
        self.assertIsNone(comparison(r,'2026-10-03','2026-10-02'))
        r['close_dates_last_60']=[]
        self.assertIsNone(comparison(r,'2026-10-02','2026-10-01'))

    def test_broken_level_uses_prior_closes_and_excludes_future(self):
        r=report(); r['masi_history'].update({'2026-10-02':90,'2026-10-05':1})
        e=market_reading(r,r['market_overview'],'2026-10-02')
        self.assertEqual(e['levels']['support_close20'],100)
        self.assertEqual(e['levels']['until'],'2026-10-01')
        self.assertEqual(e['scenarios'][0]['name'],'Poursuite baissière')
        self.assertEqual(e['ranking_coverage'],1)
        self.assertNotIn('probability',str(e))

    def test_provisional_index_cannot_create_closing_breakout(self):
        r=report();r['market_overview']['status']='provisional'
        e=market_reading(r,r['market_overview'],'2026-10-02')
        self.assertEqual(e['levels'],{})
        self.assertEqual(e['scenarios'],[])
        self.assertEqual(e['ranking_coverage'],0)
        self.assertIn('provisoire',' '.join(e['paragraphs']))

    def test_old_or_suspended_quote_cannot_receive_fresh_commentary(self):
        r=row();r['decision']='SUSPENDU'
        text=' '.join(title_reading(r,'2026-10-02','2026-10-01',-2)['paragraphs'])
        self.assertIn('aucune lecture',text)
        self.assertNotIn('surperforme',text)
        r['decision']='OBSERVABLE';r['asof']='2026-09-29'
        self.assertIsNone(title_reading(r,'2026-10-02','2026-10-01',-2)['change_pct'])

    def test_closed_briefing_excludes_future_news_and_live_quotes(self):
        r=report();r['results'][0]['intraday_quote']={'price':999}
        r['news']=[{'title':'Résultats financiers','tier':'S1','published_at':d,'url':'https://example.org/'+d,'publisher':'AMMC','tickers':['ADI']} for d in ('2026-10-02','2026-10-03')]
        b=create_briefing(r,closing_only=True)
        self.assertEqual([n['published_at'] for n in b['news']],['2026-10-02'])
        self.assertIsNone(b['focus'][0]['intraday_quote'])
        self.assertEqual(b['market_session'],'2026-10-02')
        self.assertEqual(b['coverage']['quoted_session'],1)

    def test_rendering_and_text_distinguish_documents_from_verified_facts(self):
        r=report();r['news']=[{'title':'Résultats financiers <script>','tier':'S1','published_at':'2026-10-02','url':'https://example.org/resultats','publisher':'AMMC','tickers':['ADI']}]
        b=create_briefing(r,closing_only=True);html=render_editorial(b,lambda _: '')
        for section in ('L’essentiel','Liquidité et activité','Valeurs à surveiller','Fondamentaux et catalyseurs','Macroéconomie et international','Scénarios pour la prochaine séance','Points de vigilance'):
            self.assertIn(section,html)
        self.assertIn('pas encore extrait ni validé',html)
        self.assertNotIn('<script>',html)
        self.assertIn('https://example.org/resultats',briefing_text(b))
        self.assertIn('survente ne garantit pas un rebond',html)
        self.assertIn('niveau de reconquête',html)
        self.assertIn('sans probabilités',html)


if __name__=='__main__':unittest.main()
