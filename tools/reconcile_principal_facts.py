"""Add attributed documentary candidates from a pinned, read-only principal export.

Default is a report only. Imports never certify a PDF or replace a Nour value.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'abdmoutalib207-lang/-bvc-analyzer'
SHA = re.compile(r'[0-9a-f]{40}')
MONEY_UNITS = {'MAD': 1e-6, 'KMAD': 1e-3, 'MMAD': 1}


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def plain(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold())
                   if not unicodedata.combining(c))


def scope(value):
    text = plain(value)
    if 'social' in text or 'sociaux' in text:
        return 'social'
    if 'consolid' in text:
        return 'consolidated'
    return None


def accounting_standard(value):
    text = plain(value)
    if re.search(r'\b(?:ias|ifrs)\b', text):
        return 'ifrs'
    if any(marker in text for marker in ('normes marocaines', 'normes nationales',
                                         'referentiel marocain', 'cgnc', 'avis cnc')):
        return 'national'
    return None


def checked_dimensions(key, item, source, target):
    """Check a fact's own column, accounting scope and canonical numeric unit.

    Annual report identity alone does not establish the period or the scope of
    every table inside it. Raw amounts can establish MMAD only arithmetically.
    """
    year = source['exercice']
    suffix = re.search(r'_(\d{4})$', key)
    fact_year = int(suffix[1]) if suffix else year
    if fact_year not in (year, year - 1):
        return None, 'different_fact_period'
    expected_end = f'{fact_year}-12-31'
    if item.get('period_end') is not None:
        if item['period_end'] != expected_end:
            return None, 'different_fact_period'
    else:
        column_key = 'colonne_exercice_precedent' if fact_year < year else 'colonne_exercice_clos'
        column = item.get(column_key)
        dated_base = expected_end in str(item.get('base', '')) or f'31/12/{fact_year}' in str(item.get('base', ''))
        if not dated_base and not (isinstance(column, int) and not isinstance(column, bool) and column > 0):
            return None, 'missing_fact_period'
    # An explicit conflicting date remains a conflict even with a good column.
    base_dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b', str(item.get('base', '')))
    if any(day not in (expected_end, f'31/12/{fact_year}') for day in base_dates):
        return None, 'different_fact_period'

    shares = key.startswith('nombre_actions')
    per_share = 'par_action' in key or key.startswith('bpa_')
    # Counts and legal capital belong to the issuer; financial totals require
    # an explicit social/consolidated table scope, never a sector default.
    if not shares and key != 'capital_social':
        actual_scope = scope(item.get('base'))
        target_scope = scope(target.get('accounting_basis'))
        social_key = 'social' in key or 'sociaux' in key
        group_key = 'part_groupe' in key or 'consolid' in key
        expected_scope = 'social' if social_key else 'consolidated' if group_key else target_scope
        if actual_scope is None or expected_scope is None or target_scope is None:
            return None, 'missing_accounting_scope'
        if actual_scope != expected_scope or actual_scope != target_scope:
            return None, 'different_accounting_scope'
        # IFRS and national consolidated accounts have the same scope but
        # cannot be mixed. Canonical import also cannot add a social fallback
        # to a consolidated dossier, even under an explicit *_social key.
        actual_standard = accounting_standard(item.get('base'))
        target_standard = accounting_standard(target.get('accounting_basis'))
        if actual_standard and target_standard and actual_standard != target_standard:
            return None, 'different_accounting_standard'

    candidate = deepcopy(item)
    if candidate.get('devise') not in (None, 'MAD'):
        return None, 'different_currency'
    if shares:
        if item.get('unite') != 'actions' or item['valeur'] <= 0 or int(item['valeur']) != item['valeur']:
            return None, 'invalid_share_count'
    elif per_share:
        if item.get('unite') not in ('DH', 'MAD'):
            return None, 'invalid_per_share_unit'
    else:
        unit = item.get('unite')
        raw, raw_unit = item.get('valeur_au_rapport'), item.get('unite_au_rapport')
        factor = MONEY_UNITS.get(raw_unit) if isinstance(raw_unit, str) else None
        if unit not in (None, 'MMAD'):
            return None, 'invalid_canonical_unit'
        if raw is not None:
            if not finite(raw) or factor is None:
                return None, 'unknown_report_unit'
            if not math.isclose(item['valeur'], raw * factor, rel_tol=1e-10, abs_tol=5e-7):
                return None, 'inconsistent_unit_conversion'
        elif unit is None:
            return None, 'missing_numeric_unit'
        candidate['unite'] = 'MMAD'
    candidate['period_end'] = expected_end
    return candidate, None


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
        year = source.get('exercice')
        if (not isinstance(year, int) or isinstance(year, bool)
                or source.get('exercice') != target.get('exercice')
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
            if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
                reason = 'invalid_page'
            elif item.get('url', source['url']) != source['url'] or re.match(r'https?://', str(item.get('document', ''))) and item['document'] != source['url']:
                reason = 'different_fact_document'
            candidate = None
            if reason is None:
                candidate, reason = checked_dimensions(key, item, source, target)
            if reason:
                report['rejected'].append({'symbol': symbol, 'fact': key, 'reason': reason})
                continue
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
    source = json.loads(args.source.read_text(encoding='utf-8'))
    facts = json.loads(args.facts.read_text(encoding='utf-8'))
    symbols = [s.strip().upper() for s in args.symbols.split(',') if s.strip()] if args.symbols else None
    out, report = reconcile(source, facts, args.source_commit, symbols, args.apply)
    if args.apply:
        args.facts.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
