"""Source-aware news radar. Metadata only; zero contribution to the market score."""
from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

AMMC_INDEX = "https://www.ammc.ma/fr/communiques-presse-emetteurs"
LE_MATIN_RSS = "https://lematin.ma/rss"


ALIASES = {
    'ADI':['alliances','alliances developpement immobilier'], 'ADH':['addoha','douja promotion'],
    'MNG':['managem'], 'SMI':["societe metallurgique d imiter"], 'T2S':['t2s group','t2s group holding'],
    'SNA':['sonasid'], 'STK':['stokvis'], 'MSA':['marsa maroc'], 'IBM':['ib maroc','ibmaroc'],
    'SRM':['realisations mecaniques'], 'TGCC':['tgcc'], 'BCP':['banque centrale populaire'],
    'ATW':['attijariwafa bank'], 'BOA':['bank of africa maroc'], 'IAM':['maroc telecom'],
    'CMT':['compagnie miniere de touissit'], 'CSR':['cosumar'], 'HPS':['hightech payment systems','hps'],
    'LHM':['lafargeholcim maroc','lafarge holcim maroc'], 'CIM':['ciments du maroc'],
    'AKD':['akdital'], 'RIS':['risma'], 'RDS':['residences dar saada'], 'TQA':['taqa morocco'],
}
AMBIGUOUS = {'IBM','SRM','BOA','SMI','CMT','SNA','STK'}


def _words(value):
    plain = ''.join(c for c in unicodedata.normalize('NFKD',value.lower()) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+',plain))


def associate(title, url, symbols, official, issuer_names=None):
    """Full-name matching; legacy ticker guesses are never blindly preserved."""
    title_words = ' '+_words(title)+' '
    filename = ' '+_words(urlparse(url).path.rsplit('/',1)[-1])+' '
    found=[]
    for symbol in symbols:
        aliases = list(ALIASES.get(symbol,[]))
        name=(issuer_names or {}).get(symbol,'')
        if symbol not in AMBIGUOUS and len(_words(name).split())>=2:
            aliases.append(name)
        if any(' '+_words(a)+' ' in title_words for a in aliases):
            found.append(symbol)
        elif official and symbol not in AMBIGUOUS and ' '+symbol.lower()+' ' in filename:
            found.append(symbol)
    return sorted(set(found))


def normalize(article, symbols, issuer_names=None):
    url = str(article.get("primary_url") or article.get("url") or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    official = parsed.hostname in ("www.ammc.ma", "ammc.ma") and (
        article.get("validation_status") == "listed_officially" or
        article.get("status") == "index officiel, document non analysé")
    raw_date = str(article.get("published_at") or article.get("date") or "")
    try:
        published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    title = html.unescape(re.sub(r"<[^>]+>", "", str(article.get("title") or ""))).strip()[:220]
    if not title:
        return None
    tickers = associate(title,url,symbols,official,issuer_names)
    return {"id": hashlib.sha256(url.encode()).hexdigest()[:18], "title": title,
            "url": url, "publisher": "AMMC" if official else str(article.get("publisher") or article.get("source") or parsed.hostname)[:80],
            "published_at": published.isoformat(), "tickers": tickers,
            "tier": "S1" if official else "S2", "status": "index officiel, document non analysé" if official else "alerte non vérifiée",
            "usable_for_score": False,
            "ticker_matching": "issuer_name_or_official_filename" if tickers else "unmatched",
            "classification": "DOCUMENT_LISTED" if official else "UNVERIFIED_ALERT"}


def merge_news(existing, fresh, symbols, limit=300, issuer_names=None):
    combined = {}
    for article in [*existing, *fresh]:
        normalized = normalize(article, symbols, issuer_names)
        if normalized:
            combined[normalized["id"]] = normalized
    # Never treat multiple press reports about the same event as multiple scores.
    ordered = sorted(combined.values(), key=lambda a: a["published_at"], reverse=True)
    return {"schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(),
            "role": "veille uniquement, aucun score NLP", "articles": ordered[:limit]}


class _RSS(HTMLParser):
    """Minimal parser for XML title/link/pubDate; no copied article bodies."""
    def __init__(self):
        super().__init__()
        self.tag = None
        self.current = {}
        self.items = []
    def handle_starttag(self, tag, attrs):
        if tag == "item": self.current = {}
        if tag in {"title", "link", "pubdate"}: self.tag = tag
    def handle_endtag(self, tag):
        if tag == "item" and self.current: self.items.append(self.current); self.current = {}
        if tag == self.tag: self.tag = None
    def handle_data(self, data):
        if self.tag: self.current[self.tag] = self.current.get(self.tag, "") + data


def fetch_matin(timeout=15):
    with urlopen(Request(LE_MATIN_RSS, headers={"User-Agent": "BVCAnalyzerNour/1.0"}),timeout=timeout) as res:
        body=res.read(3_000_000).decode("utf-8", "replace")
    from email.utils import parsedate_to_datetime
    parser=_RSS(); parser.feed(body)
    output=[]
    for item in parser.items[:60]:
        try: date=parsedate_to_datetime(item.get("pubdate", "")).isoformat()
        except (ValueError, TypeError): continue
        output.append({"title":item.get("title"),"url":item.get("link"),"date":date,
                       "publisher":"Le Matin", "validation_status":"unverified"})
    return output


def fetch_ammc(timeout=20):
    """Extract linked PDFs from the AMMC index; list means published, not verified content."""
    with urlopen(Request(AMMC_INDEX, headers={"User-Agent":"BVCAnalyzerNour/1.0"}),timeout=timeout) as res:
        body=res.read(3_000_000).decode("utf-8", "replace")
    found=[]
    for row in re.findall(r'<li\b[^>]*class="[^"]*actualites-row[^"]*"[^>]*>(.*?)</li>',body,re.S):
        title=re.search(r'views-field-title[^>]*>\s*<span[^>]*>(.*?)</span>',row,re.S)
        published=re.search(r'<time\b[^>]*datetime="([^"]+)"',row)
        if not (title and published): continue
        for link in re.findall(r'<a\b[^>]*href="([^"]+)"',row):
            url=urljoin(AMMC_INDEX,html.unescape(link)); host=urlparse(url).hostname
            if host not in ("www.ammc.ma","ammc.ma") or not urlparse(url).path.lower().endswith('.pdf'):
                continue
            found.append({"title":html.unescape(re.sub(r'<[^>]+>',' ',title.group(1))),
                          "url":url,"published_at":published.group(1),"publisher":"AMMC",
                          "validation_status":"listed_officially"})
    return found


def read_news(path):
    try: return json.loads(path.read_text(encoding="utf-8")).get("articles",[])
    except FileNotFoundError: return []
