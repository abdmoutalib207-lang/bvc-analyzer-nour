import copy
from datetime import datetime
import unittest
from nour.market import CASABLANCA, capture_intraday, import_session, normalized_quote
from nour.quote_view import quote_view, quote_clocks
from nour.issuer_view import issuer_heading


class QuoteClocks(unittest.TestCase):
    def setUp(self):
        self.item={'symbol':'ADI','asof':'2026-10-21','price':366,'decision':'OBSERVABLE',
                   'price_source_datetime':'21/10/2026 15:30:11','price_collected_at':'2026-10-21T16:10:00Z'}
        self.record={'name':'Alliances','sector':'Immobilier','price':366,'price_asof':'2026-10-21',
                     'candles':[{'d':'2026-10-20','c':360},{'d':'2026-10-21','o':368,'h':370,'l':360,'c':366,'v':10,'turnover_mad':3660}]}
        self.live={'price':357.35,'asof':'2026-10-22','source_datetime':'22/10/2026 13:24:10','provisional':True}

    def test_live_price_is_primary_while_canonical_close_and_score_stay_unchanged(self):
        self.item.update(intraday_quote=self.live,intraday_observed_at='2026-10-22T13:40:00Z',intraday_status='provisional')
        before=copy.deepcopy((self.item,self.record))
        view=quote_view(self.item,self.record);page=issuer_heading(self.item,self.record)
        self.assertEqual(view['price'],357.35);self.assertEqual(view['reference_session'],'2026-10-21')
        self.assertIn('data-primary-price>357,35',page)
        self.assertIn('Clôture de référence : 366,00 MAD · 21/10/2026',page)
        self.assertIn('22/10/2026 à 13h24',page);self.assertIn('Cours recueilli',page)
        self.assertEqual((self.item,self.record),before)

    def test_stale_older_or_invalid_live_quote_never_relabels_the_close(self):
        for fields in [{'intraday_status':'stale'}, {'intraday_quote':{**self.live,'asof':'2026-10-20'}},
                       {'intraday_quote':{**self.live,'price':float('nan')}},
                       {'intraday_quote':{**self.live,'asof':'bad'}}]:
            item={**self.item,'intraday_quote':self.live,**fields}
            view=quote_view(item,self.record)
            self.assertFalse(view['provisional']);self.assertEqual(view['price'],366)
            self.assertIn('21/10/2026 à 15h30',quote_clocks(view))

    def test_missing_or_different_source_clock_never_uses_collection_as_cotation(self):
        for source in [None,'bad','22/10/2026 14:00:00','21/10/2026']:
            view=quote_view({**self.item,'price_source_datetime':source},self.record)
            text=quote_clocks(view)
            self.assertIn('Heure de cotation non communiquée',text)
            self.assertIn('21/10/2026',text)
            self.assertNotIn('Cotation : <time datetime="2026-10-21T16:10',text)

    def row(self,stamp='22/10/2026 13:24:10'):
        return {'Symbol':'ADI','DateDernierCours':stamp,'Cours':357.35,'Ouverture':368,
                'PlusHaut':370,'PlusBas':350,'QteEchangee':10,'Volumes':3600}

    def test_intraday_preserves_source_time_and_does_not_change_history(self):
        fixture={'records':{'ADI':self.record}};before=copy.deepcopy(fixture)
        point=capture_intraday(fixture,[self.row()],{'ADI':'ADI'},datetime(2026,10,22,14,tzinfo=CASABLANCA))
        self.assertEqual(point['quotes']['ADI']['source_datetime'],'22/10/2026 13:24:10')
        self.assertEqual(fixture,before)
        self.assertIsNone(normalized_quote(self.row('22/10/2026'),'ADI')['source_datetime'])

    def test_accepted_unchanged_close_refreshes_only_its_own_observation_time(self):
        fixture={'records':{'ADI':self.record},'market':{}};before=copy.deepcopy(fixture)
        row=self.row('21/10/2026 15:30:11');row.update(Cours=366,PlusBas=360,Volumes=3660)
        now=datetime(2026,10,22,17,tzinfo=CASABLANCA)
        updated,details=import_session(fixture,[row],{'ADI':'ADI'},now,minimum=1)
        self.assertEqual(details['new_bars'],0);self.assertEqual(details['observations_refreshed'],1)
        rec=updated['records']['ADI']
        self.assertEqual(rec['price_source_datetime'],'21/10/2026 15:30:11')
        self.assertEqual(rec['price_collected_at'],now.isoformat())
        self.assertEqual(rec['candles'],self.record['candles']);self.assertEqual(fixture,before)
        row['QteEchangee']=11;row['Volumes']=4026
        conflict,details=import_session(fixture,[row],{'ADI':'ADI'},now,minimum=1)
        self.assertEqual(details['observations_refreshed'],0)
        self.assertNotIn('price_collected_at',conflict['records']['ADI'])
