"""Explicit, offline import from a read-only pinned source checkout/cache."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nour.history_import import reconcile

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--base-commit',required=True)
    p.add_argument('--asof',required=True)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--input',type=Path,help='Previous Nour snapshot, if replaying a pinned reconciliation')
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    result,audit=reconcile(json.loads((a.input or root/'data/market_snapshot.json').read_text()),a.source,
        json.loads((root/'data/source_codes.json').read_text()),a.asof,a.source_commit,a.base_commit)
    if a.apply:
        (root/'data/market_snapshot.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
        (root/'data/history_reconciliation.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k!='issuers'},ensure_ascii=False))
