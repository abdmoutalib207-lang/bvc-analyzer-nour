"""Replay the manually reviewed annual pages; never fetch or infer missing facts."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / 'knowledge/financial_reviews/2026-10-18.json'


def review_data():
    return json.loads(REVIEW_PATH.read_text())


def verify_pdfs(directory):
    for symbol, review in review_data()['records'].items():
        actual = 'sha256:' + hashlib.sha256((Path(directory)/(symbol+'.pdf')).read_bytes()).hexdigest()
        if actual != review['document_hash']:
            raise ValueError(f'{symbol}: reviewed PDF changed')


def merge(document):
    out = deepcopy(document)
    batch = review_data()
    for symbol, review in batch['records'].items():
        record = out['records'][symbol]
        if record.get('exercice') != review['exercise']:
            continue  # An old review must never replace a newer exercise.
        if record.get('url') != review['url']:
            raise ValueError(f'{symbol}: annual source changed; new review required')
        previous_hash = (record.get('financial_review') or {}).get('document_hash')
        if previous_hash and previous_hash != review['document_hash']:
            raise ValueError(f'{symbol}: existing review has a different document hash')
        facts = record['faits']
        record.setdefault('reconciliation_prior_oct18', deepcopy(facts))
        record['accounting_basis'] = review['basis']
        record['exercice_clos'] = '2025-12-31'
        for key, entry in review['facts'].items():
            old_hash = (facts.get(key) or {}).get('document_hash')
            if old_hash and old_hash != review['document_hash']:
                raise ValueError(f'{symbol}: conflicting primary proof for {key}')
            original, unit = entry['original_value'], entry['original_unit']
            share = key.startswith('nombre_actions')
            per_share = key.startswith('bpa_')
            divisor = 1 if share or per_share else 1000 if unit == 'KMAD' else 1000000
            facts[key] = dict(valeur=original/divisor if divisor != 1 else original,
                valeur_au_rapport=original, unite='actions' if share else 'MAD' if per_share else 'MMAD',
                unite_au_rapport=unit, page=entry['pdf_page'], printed_page=entry['printed_page'],
                period_end=entry['period_end'], devise='MAD', base=review['basis'],
                url=review['url'], document_hash=review['document_hash'],
                validation_status='selected_pages_visually_checked', note=entry['note'])
        # The earlier AGM warning described a missing denominator now reviewed.
        record['reservations'] = [n for n in record.get('reservations', []) if n !=
            'Nombre d’actions non relevé dans ces pages : BPA, PER et P/B indisponibles ; aucune déduction à partir de la capitalisation.']
        for note in review['reservations']:
            if note not in record['reservations']:
                record['reservations'].append(note)
        for reservation in review.get('calculation_reservations', []):
            if reservation not in record.setdefault('calculation_reservations', []):
                record['calculation_reservations'].append(deepcopy(reservation))
        nominal = review.get('nominal_reference')
        if nominal:
            external = dict(name='Référentiel officiel du nominal', url=nominal['url'],
                            note=nominal['note'] + f" Nominal : {nominal['nominal_mad']} MAD ; contrôle du {nominal['checked_at']}.")
            if external not in record.setdefault('external_references', []):
                record['external_references'].append(external)
        if 'financial_business' in review:
            record['financial_business'] = review['financial_business']
        record['financial_review'] = dict(reviewed_at=batch['reviewed_at'],
            document_url=review['url'], document_hash=review['document_hash'], pages=review['pages'],
            method='Lecture visuelle indépendante de pages PDF sélectionnées ; unités, périodes et périmètres contrôlés. '
                   'Titres de clôture distincts d’une moyenne pondérée. Semestres conservés sans annualisation.',
            conclusion=review['conclusion'])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pdf-directory', type=Path)
    args = parser.parse_args()
    if args.pdf_directory:
        verify_pdfs(args.pdf_directory)
    path = ROOT / 'data/facts_reference.json'
    before = json.loads(path.read_text())
    after = merge(before)
    if args.check:
        if before != after:
            raise SystemExit('Primary review October 18 is not applied')
        print('Primary review October 18: up to date')
    else:
        path.write_text(json.dumps(after, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
