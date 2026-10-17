"""Read-only retrieval contract shared with the deployable Worker via JSON.

No raw series, full financial review tree or laboratory rows go to the model.
Warnings and documentary evidence are never shortened to meet a size budget.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

POLICY_PATH = Path(__file__).resolve().parents[1] / 'knowledge/assistant_policy.json'
BASE = ('symbol', 'name', 'sector', 'url', 'price', 'price_source', 'asof',
        'decision', 'age_calendar_days', 'quality', 'history_readiness',
        'collection_conflicts', 'day_shares', 'day_turnover_mad_actual')
FUNDAMENTALS = ('exercise', 'document_url', 'period_end', 'currency', 'accounting_basis',
    'eps_mad', 'pe', 'pb', 'roe_pct', 'roe_average_equity_pct', 'roe_method',
    'earnings_mmad', 'book_value_per_share_mad', 'dividend_yield_pct', 'pnb_mmad',
    'pnb_growth_pct', 'revenue_growth_pct', 'net_debt_strict_mmad', 'net_debt_ebitda',
    'eps_denominator', 'book_denominator', 'net_debt_method', 'warnings',
    'validation_status', 'point_in_time_ready', 'coverage_pct', 'missing_metrics',
    'latest_report', 'evidence', 'financial_review', 'debt_reconciliation')


class ContextError(ValueError):
    """A safe, user-facing refusal, independent of provider/network errors."""


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(c) != 'Mn')


def policy():
    return json.loads(POLICY_PATH.read_text(encoding='utf-8'))


def question_dates(question):
    values = re.findall(r'\b(20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:20\d{2}|\d{2}))\b', question)
    if len(values) > 6:
        raise ValueError('Limitez la question à six dates.')
    result = []
    for value in values:
        if '/' in value:
            day, month, year = value.split('/')
            value = f'{"20" + year if len(year) == 2 else year}-{month.zfill(2)}-{day.zfill(2)}'
        try:
            result.append(date.fromisoformat(value).isoformat())
        except ValueError:
            raise ContextError('Date invalide. Utilisez une date réelle au format JJ/MM/AAAA.') from None
    return result


def compact_data(data):
    """A derived public retrieval index, not a second calculation engine."""
    symbols = {}
    rules = policy()
    for symbol, row in data['symbols'].items():
        allowed = set(BASE) | {k for r in rules['routes'] for k in r['fields']}
        copied = {k: deepcopy(v) for k, v in row.items() if k in allowed}
        f = row.get('fundamental') or {}
        copied['fundamental'] = {k: deepcopy(f[k]) for k in FUNDAMENTALS if k in f}
        symbols[symbol] = copied
    result = {k: deepcopy(data.get(k)) for k in
              ('analysis_date', 'snapshot_updated', 'market', 'health', 'runtime',
               'provenance', 'macro', 'masi_history')}
    result.update(schema_version='nour-assistant-context-v1', symbols=symbols,
                  policy=policy(), definitions=data.get('knowledge', {}).get('definitions', {}),
                  news=deepcopy(data.get('news') or []),
                  briefings={k: {p: deepcopy(v.get(p)) for p in
                      ('generated_for', 'market_session', 'title', 'edition_status',
                       'edition_notice', 'market_summary', 'coverage', 'limitations', 'text_url')}
                      for k, v in (data.get('briefings') or {}).items()})
    identity = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    result['snapshot_id'] = hashlib.sha256(identity.encode()).hexdigest()
    return result


def retrieve(index, symbols, question):
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 2:
        raise ValueError('Choisissez un ou deux titres, ou MASI.')
    if any(not isinstance(s, str) or s != 'MASI' and s not in index['symbols'] for s in symbols):
        raise ValueError('Titre absent du référentiel Nour.')
    rules = index['policy']
    q = normalize(question)
    routes = [r for r in rules['routes'] if re.search(r'\b(?:' + r['pattern'] + ')', q)]
    if not routes:
        routes = rules['routes'][:1]
    if any(r['id'] == 'overview' for r in routes):
        # The overview already covers numerical domains; explicit news/macro
        # requests still include their separate dated, bounded material.
        routes = [r for r in routes if r['id'] in ('overview', 'news', 'macro', 'quality')]
    fields = set(BASE) | {k for r in routes for k in r['fields']}
    keys = {k for r in routes for k in r['definitions']}
    selected = {}
    for symbol in dict.fromkeys(symbols):
        if symbol == 'MASI':
            history = index.get('masi_history') or {}
            selected[symbol] = {'market': index.get('market'),
                'history_first': min(history, default=None), 'history_last': max(history, default=None),
                'history_sessions': len(history)}
        else:
            selected[symbol] = {k: deepcopy(v) for k, v in index['symbols'][symbol].items() if k in fields}
    dates = question_dates(question)
    historical = bool(dates) and not any(r['id'] in ('news', 'macro', 'briefing') for r in routes)
    if historical:
        for symbol, row in selected.items():
            if symbol == 'MASI':
                continue
            # The numeric history remains available in the verified local CSV.
            # Until retrieved here, no current price/ratio may answer a dated request.
            selected[symbol] = {k: row[k] for k in ('symbol', 'name', 'url') if k in row}
            selected[symbol]['requested_dates'] = dates
            selected[symbol]['historical_measure_status'] = 'not_retrieved_use_verified_local_history'
    result = {'analysis_date': index['analysis_date'], 'snapshot_updated': index.get('snapshot_updated'),
        'snapshot_id': index['snapshot_id'], 'intents': [r['id'] for r in routes],
        'rules': rules['rules'], 'selected': selected,
        'definitions': {k: index['definitions'][k] for k in sorted(keys) if k in index['definitions']},
        'masi_dates': {d: (index.get('masi_history') or {}).get(d) for d in dates},
        'limitations': ['Aucune série brute ni ligne de laboratoire transmise. Pour une date de titre non fournie, consulter son historique sourcé ; ne pas inventer.']}
    intents = set(result['intents'])
    if intents & {'overview', 'quality', 'news'} and not historical:
        result['market'] = deepcopy(index.get('market'))
        result['collection'] = deepcopy(index.get('health'))
        result['provenance'] = deepcopy(index.get('provenance'))
    if intents & {'news', 'overview'}:
        eligible = [a for a in index['news'] if 'MASI' in symbols or set(symbols) & set(a.get('tickers') or [])]
        result['news'] = sorted(eligible, key=lambda a: a.get('published_at') or '', reverse=True)[:4]
        result['news_notice'] = 'Métadonnées de veille seulement ; aucune cause de variation démontrée et aucun fait comptable certifié par ce flux.'
    if 'macro' in intents:
        result['macro'] = deepcopy(index.get('macro'))
    if 'briefing' in intents:
        result['briefings'] = deepcopy(index.get('briefings'))
    if len(json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()) > rules['max_context_bytes']:
        raise ContextError('Les preuves requises dépassent le budget IA. Posez une question ciblée ; les données locales restent disponibles.')
    return result
