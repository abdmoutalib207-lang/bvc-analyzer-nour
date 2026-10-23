"""Read-only audit of sector-specific evidence and inappropriate ratios."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nour.sector_audit import audit_sector_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", default=str(ROOT / "web/report.json"))
    parser.add_argument("--json", action="store_true", help="Emit the full 80-issuer review queue")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text())
    result = audit_sector_report(report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "universe": result["universe"],
            "curated": result["curated"],
            "selected_pages_reviewed_issuers": result["selected_pages_reviewed_issuers"],
            "review_states": result["review_states"],
            "violations": result["violations"],
            "documents_certified": False,
        }, ensure_ascii=False))
    from nour.sector_validation import audit_sector_calculations
    arithmetic=audit_sector_calculations(report)
    print(json.dumps(arithmetic,ensure_ascii=False))
    if result["violations"] or arithmetic['failures']:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
