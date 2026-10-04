"""Refresh official index and press radar independently; never add news to score."""
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.market import atomic_json
from nour.news import fetch_ammc, fetch_matin, merge_news, read_news


def main():
    fixture=json.loads((ROOT/"data/market_snapshot.json").read_text())
    target=ROOT/"data/news.json"
    old=read_news(target)
    fresh=[]
    errors=[]
    for name,callback in (("AMMC",fetch_ammc),("Le Matin",fetch_matin)):
        try: fresh.extend(callback())
        except Exception as exc: errors.append(f"{name}: {exc}")
    atomic_json(ROOT/'data/news_health.json',dict(checked_at=datetime.now(timezone.utc).isoformat(),
        status='ok' if fresh and not errors else 'partial' if fresh else 'failed',
        fetched_items=len(fresh),errors=errors))
    if not fresh:
        raise RuntimeError("Aucun flux disponible : "+"; ".join(errors))
    combined=merge_news(old,fresh,fixture["symbols"],issuer_names={s:r['name'] for s,r in fixture['records'].items()})
    if combined["articles"]!=old:
        atomic_json(target,combined)
    print(f"{len(combined['articles'])} liens, {len(fresh)} nouveaux signalements, erreurs {errors}")


if __name__=="__main__": main()
