"""Refresh official index and press radar independently; never add news to score."""
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.market import atomic_json
from nour.news import fetch_ammc, fetch_matin, merge_news, read_news
from nour.macro_news import FEEDS, fetch_feed


def main():
    fixture=json.loads((ROOT/"data/market_snapshot.json").read_text())
    target=ROOT/"data/news.json"
    old=read_news(target)
    previous_articles=list(old)
    fresh=[]
    errors=[]
    sources=[]
    tasks=[('AMMC',fetch_ammc,()),('Le Matin',fetch_matin,())]
    tasks += [(feed[1],fetch_feed,(feed,)) for feed in FEEDS]
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending={pool.submit(callback,*args):name for name,callback,args in tasks}
        for future in as_completed(pending):
            name=pending[future]
            try:
                items=future.result()
                fresh.extend(items)
                sources.append(dict(name=name,status='ok' if items else 'empty',items=len(items)))
            except Exception as exc:
                errors.append(f"{name}: {str(exc)[:250]}")
                sources.append(dict(name=name,status='failed',items=0))
    atomic_json(ROOT/'data/news_health.json',dict(checked_at=datetime.now(timezone.utc).isoformat(),
        status='ok' if fresh and not errors else 'partial' if fresh else 'failed',
        fetched_items=len(fresh),errors=errors,sources=sorted(sources,key=lambda s:s['name'])))
    if not fresh:
        raise RuntimeError("Aucun flux disponible : "+"; ".join(errors))
    # Age windows apply to the new macro radar, not legacy issuer references.
    from datetime import timedelta
    from nour.macro import date_time
    now=datetime.now(timezone.utc)
    old=[a for a in old if not a.get('feed_id') or (date_time(a.get('published_at')) and
         now-timedelta(days=30 if a.get('classification')=='INSTITUTIONAL_PUBLICATION' else 7)
         <= date_time(a['published_at']) <= now)]
    combined=merge_news(old,fresh,fixture["symbols"],issuer_names={s:r['name'] for s,r in fixture['records'].items()})
    if combined["articles"]!=previous_articles:
        atomic_json(target,combined)
    print(f"{len(combined['articles'])} liens, {len(fresh)} nouveaux signalements, erreurs {errors}")


if __name__=="__main__": main()
