"""Replay selected annual primary pages; never infer or fetch financial facts."""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / 'knowledge/financial_reviews/2026-10-22.json'


def review_data():
    return json.loads(REVIEW_PATH.read_text())


def verify_pdfs(directory):
    for symbol, review in review_data()['records'].items():
        digest = 'sha256:' + hashlib.sha256((Path(directory)/(symbol+'.pdf')).read_bytes()).hexdigest()
        if digest != review['document_hash']:
            raise ValueError(f'{symbol}: reviewed PDF changed')


def merge(document):
    out = deepcopy(document)
    batch = review_data()
    for symbol, review in batch['records'].items():
        record = out['records'][symbol]
        if record.get('exercice') != review['exercise']:
            continue
        if record.get('url') != review['url']:
            raise ValueError(f'{symbol}: annual source changed')
        previous_hash = (record.get('financial_review') or {}).get('document_hash')
        if previous_hash and previous_hash != review['document_hash']:
            raise ValueError(f'{symbol}: primary review hash conflict')
        facts = record['faits']
        keys = set(review['facts']) | set(review.get('remove_keys', []))
        record.setdefault('reconciliation_prior_oct22', {
            key: deepcopy(facts.get(key)) for key in sorted(keys)})
        record['accounting_basis'] = review['basis']
        record['exercice_clos'] = '2025-12-31'
        for key in keys:
            old_hash = (facts.get(key) or {}).get('document_hash')
            if old_hash and old_hash != review['document_hash']:
                raise ValueError(f'{symbol}: conflicting evidence for {key}')
        for key in review.get('remove_keys', []):
            facts.pop(key, None)
        for key, entry in review['facts'].items():
            unit = entry['original_unit']
            if unit not in ('MAD', 'KMAD', 'MMAD', 'actions'):
                raise ValueError(f'{symbol}: unsupported reviewed unit')
            divisor = {'MAD': 1000000, 'KMAD': 1000, 'MMAD': 1, 'actions': 1}[unit]
            number = Decimal(str(entry['original_value'])) / divisor
            facts[key] = dict(valeur=int(number) if unit == 'actions' else float(number),
                valeur_au_rapport=entry['original_value'], unite='actions' if unit == 'actions' else 'MMAD',
                unite_au_rapport=unit, page=entry['pdf_page'], printed_page=entry['printed_page'],
                period_end=entry['period_end'], devise='MAD', base=review['basis'],
                url=review['url'], document_hash=review['document_hash'],
                validation_status='selected_pages_visually_checked', note=entry['note'])
        for note in review['reservations']:
            if note not in record.setdefault('reservations', []):
                record['reservations'].append(note)
        for reference in review.get('external_references', []):
            if reference not in record.setdefault('external_references', []):
                record['external_references'].append(deepcopy(reference))
        record['financial_review'] = dict(reviewed_at=batch['reviewed_at'],
            document_url=review['url'], document_hash=review['document_hash'], pages=review['pages'],
            method='Pages annuelles sélectionnées téléchargées, rendues et lues ; RNPG, social et total distincts. '
                   'Titres de clôture indicatifs, jamais moyenne pondérée supposée ; semestres inchangés.',
            conclusion=review['conclusion'])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pdf-directory', type=Path)
    args = parser.parse_args()
    if args.pdf_directory:
        verify_pdfs(args.pdf_directory)
    path = ROOT/'data/facts_reference.json'
    before = json.loads(path.read_text())
    after = merge(before)
    if args.check:
        if before != after:
            raise SystemExit('Primary review October 22 is not applied')
        print('Primary review October 22: up to date')
    else:
        path.write_text(json.dumps(after, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
