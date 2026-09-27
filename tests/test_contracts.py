"""High-risk contracts at the ingestion / score / publication boundaries."""
import copy
import json
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from nour.market import import_session, normalized_quote
from nour.engine import build_report
from nour.briefing import create_briefing, level_scenario, market_relevant
from nour.news import merge_news

ROOT = Path(__file__).resolve().parents[1]


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT/'data/market_snapshot.json').read_text())
        cls.codes = json.loads((ROOT/'data/source_codes.json').read_text())

    def test_inverted_official_codes_and_true_extremes(self):
        self.assertEqual(self.codes['STK'], 'SNA')
        self.assertEqual(self.codes['SNA'], 'SID')
        latest = max(date.fromisoformat(r['price_asof']) for r in self.fixture['records'].values()
                     if r.get('price_asof'))
        session = max(latest, date.today()) + timedelta(days=1)
        session_text = session.strftime('%d/%m/%Y')
        lines = []
        for ticker in self.fixture['symbols'][:32]:
            lines.append({'Symbol': self.codes[ticker], 'DateDernierCours':session_text,
                          'Cours':100, 'Ouverture':101, 'PlusHaut':103,
                          'PlusBas':98, 'QteEchangee':1000, 'Volumes':100000})
        # Add both members of the collision-prone pair even if not in first 32.
        for ticker in ('STK', 'SNA'):
            lines.append({'Symbol':self.codes[ticker], 'DateDernierCours':session_text,
                          'Cours':100, 'Ouverture':101, 'PlusHaut':103,
                          'PlusBas':98, 'QteEchangee':1000, 'Volumes':100000})
        # Unique symbols if first 32 happened to contain one of them.
        lines=list({x['Symbol']:x for x in lines}.values())
        original = self.fixture['records']['STK']['price_asof']
        updated, summary = import_session(self.fixture, lines, self.codes,
            now=datetime(session.year,session.month,session.day,19,tzinfo=ZoneInfo('Africa/Casablanca')))
        self.assertGreaterEqual(summary['active_quotes'], 20)
        self.assertEqual(updated['records']['STK']['candles'][-1]['h'],103)
        self.assertEqual(updated['records']['SNA']['candles'][-1]['l'],98)
        self.assertEqual(self.fixture['records']['STK']['price_asof'],original)
        self.assertTrue(updated['market']['masi']['stale'])

    def test_one_historical_conflict_does_not_block_other_tickers(self):
        fixture = copy.deepcopy(self.fixture)
        latest = max(date.fromisoformat(r['price_asof']) for r in self.fixture['records'].values()
                     if r.get('price_asof'))
        # Simulate ADI needing the current session while ADH has a conflicting
        # previously published candle for that very session.
        self.assertEqual(fixture['records']['ADI']['candles'][-1]['d'], latest.isoformat())
        fixture['records']['ADI']['candles'].pop()
        fixture['records']['ADI']['price_asof'] = fixture['records']['ADI']['candles'][-1]['d']
        lines = []
        for ticker in self.fixture['symbols'][:35]:
            lines.append({'Symbol':self.codes[ticker], 'DateDernierCours': latest.strftime('%d/%m/%Y'),
                          'Cours':100,'Ouverture':101,'PlusHaut':103,'PlusBas':98,
                          'QteEchangee':1000,'Volumes':100000})
        original = fixture['records']['ADH']['candles'][-1].copy()
        updated, summary = import_session(fixture, lines, self.codes,
            now=datetime(latest.year, latest.month, latest.day,19,tzinfo=ZoneInfo('Africa/Casablanca')))
        self.assertIn('ADH',[c['symbol'] for c in summary['conflicts']])
        self.assertEqual(updated['records']['ADH']['candles'][-1],original)
        self.assertGreaterEqual(summary['new_bars'],1)
        self.assertEqual(updated['records']['ADI']['candles'][-1]['d'], latest.isoformat())

    def test_no_fabricated_candle_and_cancelled_session(self):
        row={'DateDernierCours':'28/09/2026','Cours':100,'Ouverture':100,
             'PlusHaut':None,'PlusBas':99,'QteEchangee':10,'Volumes':1000}
        with self.assertRaises(ValueError): normalized_quote(row,'ADI')
        row['DateDernierCours']='17/09/2026'
        self.assertIsNone(normalized_quote(row,'ADI'))
        row.update(DateDernierCours='28/09/2026',PlusHaut=101,QteEchangee=0)
        self.assertIsNone(normalized_quote(row,'ADI'))

    def test_no_news_or_legacy_signal_changes_canonical_score(self):
        base=build_report(self.fixture,'2026-09-27')
        sample={'title':'Bonne nouvelle ADI','url':'https://example.org/adi',
                'date':'2026-09-27','tickers':['ADI']}
        article=merge_news([], [sample], self.fixture['symbols'])['articles'][0]
        with_news=build_report(self.fixture,'2026-09-27',news=[article])
        b={x['symbol']:x['canonical_score'] for x in base['results']}
        n={x['symbol']:x['canonical_score'] for x in with_news['results']}
        self.assertEqual(b,n)
        self.assertFalse(article['usable_for_score'])
        brief=create_briefing(with_news)
        self.assertEqual(brief['news_role'],'veille uniquement')
        self.assertTrue(all('scenario' in f for f in brief['focus']))

    def test_market_briefing_rejects_irrelevant_headlines(self):
        self.assertFalse(market_relevant({'title':'Concert au théâtre national', 'tier':'S2'}))
        self.assertFalse(market_relevant({'title':'Résultats des élections', 'tier':'S2'}))
        self.assertTrue(market_relevant({'title':'Résultats financiers semestriels', 'tier':'S2'}))
        self.assertTrue(market_relevant({'title':'Publication d’un émetteur', 'tier':'S1'}))

    def test_briefing_describes_broken_support_without_claiming_it_holds(self):
        self.assertIn('sous le support', level_scenario(282,287,335))
        self.assertIn('au-dessus de la résistance', level_scenario(342,287,335))
        self.assertIn('tenue du support', level_scenario(300,287,335))
        self.assertIn('après la reprise', level_scenario(300,287,335,True))


if __name__=='__main__': unittest.main()
