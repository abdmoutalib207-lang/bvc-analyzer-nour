"""Replay page-checked supplemental facts without changing legacy score inputs."""
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.market import atomic_json


def reconcile(payload, review):
    out=deepcopy(payload)
    for symbol,facts in review['records'].items():
        if symbol not in out['records']:raise ValueError('Unknown issuer')
        previous=out['records'][symbol].setdefault('sector_faits',{})
        for key,fact in facts.items():
            if key not in previous:
                previous[key]=deepcopy(fact)
            elif previous[key] != fact:
                # Historical replay must not discard additions or roll back a
                # later reviewed correction. Equal-age/untracked conflicts
                # require a new review rather than a last-writer-wins merge.
                try:
                    old_date=datetime.fromisoformat(previous[key]['reviewed_at'].replace('Z','+00:00')).date()
                    incoming_date=datetime.fromisoformat(fact.get('reviewed_at',review['reviewed_at']).replace('Z','+00:00')).date()
                except (KeyError,TypeError,ValueError,AttributeError):
                    raise ValueError(f'{symbol}/{key}: conflicting supplemental evidence without review dates') from None
                if old_date <= incoming_date:
                    raise ValueError(f'{symbol}/{key}: conflicting supplemental evidence; new review required')
    return out

if __name__=='__main__':
    path=ROOT/'data/facts_reference.json'
    payload=reconcile(json.loads(path.read_text()),json.loads((ROOT/'knowledge/financial_reviews/2026-10-23-sector.json').read_text()))
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n');temp.replace(path)
