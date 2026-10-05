"""Fetch public global quotes independently, preserving dated observations on failure."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.macro import fetch_scan, parse_scan, merge_snapshot
from nour.market import atomic_json


def main():
    target = ROOT/'data/macro.json'
    previous = json.loads(target.read_text()) if target.exists() else {}
    errors = {}
    try:
        payload = fetch_scan()
        now = datetime.now(timezone.utc)
        fresh, errors = parse_scan(payload, now)
    except Exception as exc:
        fresh = {}
        now = datetime.now(timezone.utc)
        errors['collector'] = str(exc)[:300]
    snapshot = merge_snapshot(previous, fresh, errors, now)
    atomic_json(target, snapshot)
    print(f"Macro : {len(fresh)}/12 observations collectées ; état {snapshot['status']} ; {snapshot['errors']}")
    if not fresh:
        raise RuntimeError('Collecte macro indisponible ; observations datées conservées')


if __name__ == '__main__': main()
