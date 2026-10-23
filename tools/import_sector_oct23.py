"""Replay page-checked supplemental facts without changing legacy score inputs."""
import json
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.market import atomic_json


def reconcile(payload, review):
    out=deepcopy(payload)
    for symbol,facts in review['records'].items():
        if symbol not in out['records']:raise ValueError('Unknown issuer')
        out['records'][symbol]['sector_faits']=deepcopy(facts)
    return out

if __name__=='__main__':
    path=ROOT/'data/facts_reference.json'
    payload=reconcile(json.loads(path.read_text()),json.loads((ROOT/'knowledge/financial_reviews/2026-10-23-sector.json').read_text()))
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n');temp.replace(path)
