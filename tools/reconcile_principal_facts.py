"""Add attributed documentary candidates from a pinned, read-only principal export.

Default is a report only. Imports never certify a PDF or replace a Nour value.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'abdmoutalib207-lang/-bvc-analyzer'
SHA = re.compile(r'[0-9a-f]{40}')


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def reconcile(principal, nour, source_commit, symbols=None, apply=False):
    if not SHA.fullmatch(source_commit):
        raise ValueError('A full pinned source commit is required')
    out = deepcopy(nour)
    records = out['records']
    selected = set(symbols) if symbols else set(records)
    if not selected <= set(records):
        raise ValueError('Unknown Nour symbols')
    report = {'source_repository': REPOSITORY, 'source_commit': source_commit,
              'source_path': 'pipeline/faits_financiers.json', 'applied': apply,
              'candidates': [], 'different_values': [], 'rejected': [],
              'documents_certified': False}
    for symbol in sorted(selected):
        source = principal.get(symbol)
        target = records[symbol]
        if not isinstance(source, dict):
            continue
        if (source.get('exercice') != target.get('exercice')
                or not source.get('url') or source.get('url') != target.get('url')):
            report['rejected'].append({'symbol': symbol, 'reason': 'period_or_document_mismatch'})
            continue
        for key, item in source.get('faits', {}).items():
            if not isinstance(item, dict) or not finite(item.get('valeur')):
                continue
            old = target.get('faits', {}).get(key)
            if old is not None:
                if isinstance(old, dict) and old.get('valeur') != item['valeur']:
                    report['different_values'].append({'symbol': symbol, 'fact': key,
                        'nour_value': old.get('valeur'), 'principal_value': item['valeur']})
                continue
            reason = None
            page = item.get('page')
            base = str(item.get('base', '')).casefold()
            target_base = str(target.get('accounting_basis', '')).casefold()
            if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
                reason = 'invalid_page'
            elif ('part_groupe' in key or key.endswith('_consolides') or key.endswith('_consolide')) and ('social' in base or 'sociaux' in base):
                reason = 'social_amount_under_group_key'
            elif ('consolid' in target_base and ('social' in base or 'sociaux' in base)) or (('social' in target_base or 'sociaux' in target_base) and 'consolid' in base):
                reason = 'different_accounting_scope'
            elif item.get('url', source['url']) != source['url'] or str(item.get('document', '')).startswith('https://') and item['document'] != source['url']:
                reason = 'different_fact_document'
            elif key.startswith('nombre_actions') and (item['valeur'] <= 0 or int(item['valeur']) != item['valeur'] or item.get('unite') not in (None, 'actions')):
                reason = 'invalid_share_count'
            elif item.get('period_end') is not None and str(item['period_end']) not in (f"{source['exercice']}-12-31", f"{source['exercice'] - 1}-12-31" if key.endswith(str(source['exercice'] - 1)) else ''):
                reason = 'different_fact_period'
            if reason:
                report['rejected'].append({'symbol': symbol, 'fact': key, 'reason': reason})
                continue
            candidate = deepcopy(item)
            # Do not copy another operator's visual-review assertion or hash.
            for name in ('document_hash', 'validation_status', 'reviewed_on', 'reviewed_at'):
                candidate.pop(name, None)
            candidate['validation_status'] = 'referenced_import_not_independent_audit'
            candidate['import_provenance'] = {'repository': REPOSITORY, 'commit': source_commit,
                'path': 'pipeline/faits_financiers.json', 'document_url': source['url'],
                'source_fact': key, 'source_symbol': symbol}
            report['candidates'].append({'symbol': symbol, 'fact': key,
                'value': item['valeur'], 'page': page, 'document_url': source['url']})
            if apply:
                target.setdefault('faits', {})[key] = candidate
    return out, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--facts', type=Path, default=ROOT / 'data/facts_reference.json')
    parser.add_argument('--symbols', help='Comma-separated Nour symbols')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.source.resolve() == args.facts.resolve():
        parser.error('The read-only source cannot be the output facts file')
    source = json.loads(args.source.read_text())
    facts = json.loads(args.facts.read_text())
    symbols = [s.strip().upper() for s in args.symbols.split(',') if s.strip()] if args.symbols else None
    out, report = reconcile(source, facts, args.source_commit, symbols, args.apply)
    if args.apply:
        args.facts.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
