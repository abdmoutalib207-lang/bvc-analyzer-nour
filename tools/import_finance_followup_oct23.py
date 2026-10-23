"""Replay reviewed supplemental facts, preserving every legacy financial input."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'knowledge/financial_reviews/2026-10-23-followup.json'


def reconcile(payload, review):
    out = deepcopy(payload)
    for symbol, entry in review['records'].items():
        record = out['records'][symbol]
        if record.get('url') != entry['url'] or record.get('exercice') != entry['exercise']:
            raise ValueError(f'{symbol}: source or period changed; new review required')
        previous = record.setdefault('sector_faits', {})
        for key, fact in entry['facts'].items():
            if key in previous and previous[key] != fact:
                raise ValueError(f'{symbol}/{key}: conflicting supplemental evidence')
            previous[key] = deepcopy(fact)
        record['sector_review_followup'] = {
            k: deepcopy(entry[k]) for k in ('document_hash', 'pages', 'reservations')}
        record['sector_review_followup']['reviewed_at'] = review['reviewed_at']
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pdf-directory', type=Path)
    args = parser.parse_args()
    review = json.loads(MANIFEST.read_text())
    if args.pdf_directory:
        for symbol, entry in review['reviewed_dossiers'].items():
            digest = 'sha256:' + hashlib.sha256((args.pdf_directory/(symbol+'.pdf')).read_bytes()).hexdigest()
            if digest != entry['document_hash']:
                raise ValueError(f'{symbol}: reviewed PDF changed')
    path = ROOT/'data/facts_reference.json'
    before = json.loads(path.read_text())
    after = reconcile(before, review)
    if args.check:
        if before != after:
            raise SystemExit('Supplemental review not applied')
        print('October 23 follow-up: up to date')
    else:
        temp = path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(after, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        temp.replace(path)


if __name__ == '__main__':
    main()
