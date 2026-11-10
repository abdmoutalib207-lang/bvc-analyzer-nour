"""Refresh a bounded secondary comparison; no canonical financial writes."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.market import atomic_json
from nour.screener_reconciliation import MAX_SCRIPT, collect


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Saved app.js bytes; decoded as data, never executed')
    parser.add_argument('--now', help='Explicit timezone-qualified observation time')
    parser.add_argument('--root', type=Path, default=ROOT, help='Isolated output root, also used by offline tests')
    args = parser.parse_args(argv)
    data = args.root / 'data'
    nour = json.loads((data / 'facts_reference.json').read_text())
    path = data / 'screener_reconciliation.json'
    previous = json.loads(path.read_text()) if path.exists() else None
    script = None
    if args.input:
        with args.input.open('rb') as source:
            script = source.read(MAX_SCRIPT + 1)
    snapshot = data / 'market_snapshot.json'
    symbols = json.loads(snapshot.read_text()).get('symbols') if snapshot.exists() else None
    registry = data / 'source_codes.json'
    codes = json.loads(registry.read_text()) if registry.exists() else None
    report = collect(nour, previous, now=args.now, script=script, symbols=symbols, source_codes=codes)
    atomic_json(path, report)
    atomic_json(args.root / 'web' / 'screener-reconciliation.json', report)
    print(json.dumps({k: report.get(k) for k in ('status', 'checked_at', 'source_generated_at', 'summary', 'automatic_corrections')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
