import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from nour.macro import INSTRUMENTS, parse_scan, merge_snapshot, context_view, mode_label
from nour.macro_news import REGISTRY, parse_feed, scope_for
from nour.news import normalize, merge_news
from nour.macro_view import markets_html, radar_html
from nour.engine import build_report
from nour.briefing import create_briefing

NOW=datetime(2026,10,5,18,0,tzinfo=timezone.utc)


def payload(tickers=None):
    return {'data':[{'s':ticker,'d':[name,100,0,currency,NOW.timestamp()-60,'delayed_streaming_600']}
                   for ticker,name,group,unit,currency in INSTRUMENTS if tickers is None or ticker in tickers]}


class MacroTest(unittest.TestCase):
    def test_exact_instruments_and_units(self):
        quotes,errors=parse_scan(payload(),NOW)
        self.assertEqual(len(quotes),12);self.assertFalse(errors)
        rows=[r for g in context_view(merge_snapshot({},quotes,{},NOW),NOW)['groups'] for r in g['rows']]
        self.assertEqual(len(rows),12)
        self.assertEqual(next(r['unit'] for r in rows if r['ticker']=='COMEX:HG1!'),'USD / livre')
        self.assertEqual(quotes['SP:SPX']['change_pct'],0)

    def test_response_order_does_not_define_identity(self):
        p=payload();p['data'].reverse();p['data'].append({'s':'UNKNOWN','d':[]})
        q,e=parse_scan(p,NOW)
        self.assertEqual(q['SP:SPX']['description'],'S&P 500');self.assertFalse(e)

    def test_invalid_numbers_dates_and_currency(self):
        for index,value in ((1,True),(1,float('nan')),(1,float('inf')),(1,-1),
                            (2,float('inf')),(4,True),(4,0),(4,1e100),(4,NOW.timestamp()+1),(3,'EUR')):
            with self.subTest(index=index,value=value):
                p=payload(['COMEX:GC1!']);p['data'][0]['d'][index]=value
                q,e=parse_scan(p,NOW);self.assertFalse(q);self.assertIn('COMEX:GC1!',e)

    def test_missing_timestamp_or_duplicate_is_unavailable(self):
        p=payload(['SP:SPX']);p['data'][0]['d'][4]=None
        self.assertFalse(parse_scan(p,NOW)[0])
        p=payload(['SP:SPX']);p['data'].append(copy.deepcopy(p['data'][0]))
        self.assertFalse(parse_scan(p,NOW)[0])

    def test_missing_change_not_fabricated(self):
        p=payload(['SP:SPX']);p['data'][0]['d'][2]=None
        q,e=parse_scan(p,NOW);self.assertIsNone(q['SP:SPX']['change_pct'])

    def test_partial_collection_keeps_original_dates(self):
        quotes,_=parse_scan(payload(),NOW)
        old=merge_snapshot({},quotes,{},NOW)
        later=NOW+timedelta(hours=1)
        updated=merge_snapshot(old,{}, {'collector':'timeout'},later)
        self.assertEqual(updated['status'],'failed')
        self.assertEqual(updated['quotes']['SP:SPX']['observed_at'],old['quotes']['SP:SPX']['observed_at'])
        self.assertEqual(updated['quotes']['SP:SPX']['collected_at'],old['quotes']['SP:SPX']['collected_at'])
        self.assertEqual(context_view(updated,later)['groups'][0]['rows'][0]['state'],'cached')

    def test_regression_and_conflict_keep_archive(self):
        quotes,_=parse_scan(payload(),NOW);old=merge_snapshot({},quotes,{},NOW)
        new=copy.deepcopy(quotes);new['SP:SPX']['value']=123
        updated=merge_snapshot(old,new,{},NOW)
        self.assertEqual(updated['quotes']['SP:SPX']['value'],100)
        self.assertIn('SP:SPX',updated['errors'])
        new['SP:SPX']['observed_at']=(NOW-timedelta(days=1)).isoformat()
        self.assertEqual(merge_snapshot(old,new,{},NOW)['quotes']['SP:SPX']['value'],100)

    def test_cutoff_excludes_later_observations(self):
        q,_=parse_scan(payload(),NOW)
        view=context_view(merge_snapshot({},q,{},NOW),NOW-timedelta(days=1))
        self.assertTrue(all(r['value'] is None for g in view['groups'] for r in g['rows']))
        self.assertNotIn('100,00',markets_html(view))

    def test_visible_dates_modes_and_missing_placeholders(self):
        q,_=parse_scan(payload(),NOW)
        html=markets_html(context_view(merge_snapshot({},q,{},NOW),NOW))
        self.assertEqual(html.count('data-macro-ticker='),12)
        self.assertIn('2026-10-05T17:59:00+00:00',html)
        self.assertIn('Différé source : 10 min',html)
        self.assertIn('futures continus',html)
        self.assertNotIn('temps réel',mode_label('streaming'))
        self.assertIn('non renseigné',mode_label(None))


class MacroNewsTest(unittest.TestCase):
    def item(self,**extra):
        return dict(title='Fed : taux directeur',url='https://www.federalreserve.gov/newsevents/pressreleases/monetary.htm',
            published_at=NOW.isoformat(),feed_id='fed',**extra)

    def test_institutional_host_not_google_relay(self):
        self.assertEqual(normalize(self.item(),[])['tier'],'S1')
        raw=self.item();raw['url']='https://news.google.com/rss/articles/123'
        self.assertEqual(normalize(raw,[])['tier'],'S2')
        raw['url']='https://www.federalreserve.gov.evil.example/article'
        self.assertEqual(normalize(raw,[])['tier'],'S2')
        raw['url']='https://www.ecb.europa.eu/article'
        self.assertEqual(normalize(raw,[])['tier'],'S2')

    def test_scope_distinct_from_category_and_stable_after_merge(self):
        raw=self.item();raw['title']='Bank Al-Maghrib : inflation au Maroc'
        a=normalize(raw,[])
        self.assertEqual(a['scope'],'MAROC');self.assertEqual(a['category'],'macro')
        b=merge_news([a],[],[])['articles'][0]
        self.assertEqual(b['scope'],'MAROC');self.assertEqual(b['tier'],'S1')
        self.assertFalse(b['usable_for_score'])
        self.assertEqual(scope_for('Inflation aux États-Unis',[],'INTL'),'INTL')
        self.assertEqual(scope_for('Économie mondiale',[]),'UNKNOWN')

    def test_rss_uses_publication_date_and_excludes_future_missing_or_old(self):
        xml=b'''<rss><channel><item><title>Rates</title><link>https://www.federalreserve.gov/article</link><pubDate>Mon, 05 Oct 2026 17:00:00 GMT</pubDate></item>
        <item><title>Future</title><link>https://www.federalreserve.gov/future</link><pubDate>Tue, 06 Oct 2026 17:00:00 GMT</pubDate></item>
        <item><title>Missing date</title><link>https://www.federalreserve.gov/undated</link></item>
        <item><title>Old</title><link>https://www.federalreserve.gov/old</link><pubDate>Mon, 01 Jun 2026 17:00:00 GMT</pubDate></item></channel></rss>'''
        articles=parse_feed(xml,REGISTRY['fed'],NOW)
        self.assertEqual(len(articles),1);self.assertEqual(articles[0]['published_at'],'2026-10-05T17:00:00+00:00')

    def test_atom_supported_and_untrusted_text_escaped(self):
        xml=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>ECB &amp; rates</title><link href="https://www.ecb.europa.eu/article"/><published>2026-10-05T17:00:00Z</published></entry></feed>'''
        articles=parse_feed(xml,REGISTRY['ecb'],NOW)
        self.assertEqual(len(articles),1)
        a=normalize(articles[0],[]);a['title']='<script>alert(1)</script>'
        rendered=radar_html([a]);self.assertIn('&lt;script&gt;',rendered)
        for id in ('news-scope','news-category','news-tier','news-reset','news-count'):
            self.assertIn(f'id="{id}"',rendered)

    def test_radar_keeps_documents_and_macro_when_crowded(self):
        existing=[dict(title='Document',url=f'https://www.ammc.ma/file{i}.pdf',published_at=NOW.isoformat(),validation_status='listed_officially') for i in range(300)]
        raw=self.item()
        articles=merge_news(existing,[raw],[])['articles']
        self.assertEqual(len(articles),300)
        self.assertTrue(any(a.get('feed_id')=='fed' for a in articles))
        self.assertTrue(any(a['classification']=='DOCUMENT_LISTED' for a in articles))

    def test_no_effect_on_scores_and_dated_closing_brief(self):
        root=Path(__file__).resolve().parents[1]
        fixture=json.loads((root/'data/market_snapshot.json').read_text())
        base=build_report(fixture,'2026-10-05')
        with_news=build_report(fixture,'2026-10-05',news=[normalize(self.item(),fixture['symbols'])])
        self.assertEqual(base['results'],with_news['results'])
        q,_=parse_scan(payload(),NOW)
        base['macro_source']=merge_snapshot({},q,{},NOW)
        base['market_overview']={'asof':'2026-10-02'}
        brief=create_briefing(base,closing_only=True)
        self.assertTrue(all(r['value'] is None for g in brief['macro']['groups'] for r in g['rows']))


if __name__=='__main__': unittest.main()
