"""Metadata-only macro/international feeds. No sentiment or decision-making NLP."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from .news import _words

GNEWS = 'https://news.google.com/rss/search?q={}&hl=fr&gl=MA&ceid=MA:fr'
FEEDS = [
    ('bam', 'Bank Al-Maghrib · relais presse', GNEWS.format(quote('site:bkam.ma')), 'macro', 'MAROC', None),
    ('hcp', 'HCP · publications', 'https://www.hcp.ma/xml/syndication.rss', 'macro', 'MAROC', 'www.hcp.ma'),
    ('mef', 'Finances Maroc · relais presse', GNEWS.format(quote('site:finances.gov.ma')), 'economie', 'MAROC', None),
    ('fed', 'Fed · politique monétaire', 'https://www.federalreserve.gov/feeds/press_monetary.xml', 'macro', 'INTL', 'www.federalreserve.gov'),
    ('ecb', 'BCE · publications', 'https://www.ecb.europa.eu/rss/press.html', 'macro', 'INTL', 'www.ecb.europa.eu'),
    ('inflation', 'Inflation US / zone euro · presse', GNEWS.format(quote('inflation États-Unis zone euro chiffres')), 'macro', 'INTL', None),
    ('fed_presse', 'Fed · presse francophone', GNEWS.format(quote('Réserve fédérale taux directeur Fed marchés')), 'macro', 'INTL', None),
    ('ecb_presse', 'BCE · presse francophone', GNEWS.format(quote('BCE taux directeur zone euro politique monétaire')), 'macro', 'INTL', None),
    ('proche_orient', 'Proche-Orient · presse', GNEWS.format(quote('Proche-Orient Moyen-Orient tensions marchés pétrole')), 'geopolitique', 'INTL', None),
    ('partenaires', 'Europe / partenaires du Maroc', GNEWS.format(quote('économie Espagne France croissance échanges Maroc')), 'economie', 'INTL', None),
    ('oilprice', 'OilPrice', 'https://oilprice.com/rss/main', 'commodites', 'INTL', None),
    ('mining', 'Mining.com', 'https://www.mining.com/rss/', 'commodites', 'INTL', None),
    ('rfi', 'RFI · économie', 'https://www.rfi.fr/fr/economie/rss', 'economie', 'INTL', None),
    ('france24', 'France 24 · économie', 'https://www.france24.com/fr/economie/rss', 'economie', 'INTL', None),
    ('financialafrik', 'Financial Afrik', 'https://www.financialafrik.com/feed/', 'economie', 'UNKNOWN', None),
]
REGISTRY = {f[0]: f for f in FEEDS}
CATEGORIES = {'bvc':'Bourse', 'economie':'Économie', 'macro':'Macroéconomie',
              'geopolitique':'Géopolitique', 'commodites':'Matières premières', 'autre':'Autres'}
SCOPES = {'MAROC':'Maroc', 'INTL':'International', 'UNKNOWN':'Périmètre non établi'}


def scope_for(title, tickers, default='UNKNOWN'):
    words = ' '+_words(title)+' '
    if tickers or any(' '+w+' ' in words for w in ('maroc','marocaine','marocain','rabat','casablanca','dirham','bank al maghrib','hcp')):
        return 'MAROC'
    return default if default in SCOPES else 'UNKNOWN'


def parse_feed(body, feed, now):
    feed_id, name, feed_url, category, scope, official_host = feed
    root = ET.fromstring(body)
    output = []
    for entry in root.iter():
        if entry.tag.rsplit('}',1)[-1] not in ('item', 'entry'): continue
        fields = {}
        for child in entry:
            tag = child.tag.rsplit('}',1)[-1]
            if tag == 'link' and child.attrib.get('href') and child.attrib.get('rel','alternate')=='alternate':
                fields['link'] = child.attrib['href']
            elif child.text: fields[tag] = child.text.strip()
        raw_date = fields.get('pubDate') or fields.get('published') or fields.get('updated')
        if not raw_date: continue
        try:
            try: date = datetime.fromisoformat(raw_date.replace('Z','+00:00'))
            except ValueError: date = parsedate_to_datetime(raw_date)
            if not date.tzinfo: continue
            date = date.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError): continue
        # Source dates only. No collection timestamp substituted for publication.
        if not now-timedelta(days=30 if official_host else 7) <= date <= now: continue
        link = fields.get('link','')
        if urlparse(link).scheme != 'https': continue
        output.append(dict(title=fields.get('title'), url=link, published_at=date.isoformat(),
            publisher=name, feed_id=feed_id, feed_url=feed_url, category=category,
            scope=scope, validation_status='institutional_feed' if official_host else 'unverified'))
    return sorted(output, key=lambda a:a['published_at'], reverse=True)[:12]


def fetch_feed(feed, timeout=12):
    with urlopen(Request(feed[2], headers={'User-Agent':'BVCAnalyzerNour/1.0'}),timeout=timeout) as res:
        body = res.read(3_000_000)
    return parse_feed(body, feed, datetime.now(timezone.utc))
