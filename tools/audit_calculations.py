"""Fail CI on an arithmetic discrepancy for any issuer in the supplied universe."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.calculation_audit import audit_calculations


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT/'web/report.json')
    parser.add_argument('--snapshot', type=Path, default=ROOT/'data/market_snapshot.json')
    args = parser.parse_args()
    result = audit_calculations(json.loads(args.snapshot.read_text()), json.loads(args.report.read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(bool(result['failures']))
