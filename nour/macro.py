"""Independent international snapshots. Context only, never a scoring input."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from urllib.request import Request, urlopen

SCANNER = 'https://scanner.tradingview.com/global/scan'
COLUMNS = ['description', 'close', 'change', 'currency', 'update_time', 'update_mode']
# Identical instruments to the principal engine, inspected read-only at f97b467.
INSTRUMENTS = [
    ('SP:SPX', 'S&P 500', 'Indices actions', 'points', None),
    ('DJ:DJI', 'Dow Jones', 'Indices actions', 'points', None),
    ('EURONEXT:PX1', 'CAC 40', 'Indices actions', 'points', None),
    ('TVC:NI225', 'Nikkei 225', 'Indices actions', 'points', None),
    ('FX_IDC:USDMAD', 'USD/MAD', 'Risque et devises', 'MAD / USD', 'MAD'),
    ('FX_IDC:EURMAD', 'EUR/MAD', 'Risque et devises', 'MAD / EUR', 'MAD'),
    ('CBOE:VIX', 'VIX', 'Risque et devises', 'points', None),
    ('TVC:DXY', 'Indice dollar', 'Risque et devises', 'points', None),
    ('COMEX:GC1!', 'Or · futures', 'Matières premières', 'USD / once troy', 'USD'),
    ('ICEEUR:BRN1!', 'Brent · futures', 'Matières premières', 'USD / baril', 'USD'),
    ('COMEX:HG1!', 'Cuivre · futures', 'Matières premières', 'USD / livre', 'USD'),
    ('ICEEUR:ATW1!', 'Charbon API2 · futures', 'Matières premières', 'USD / tonne', 'USD'),
]
CONTRACTS = {row[0]: row for row in INSTRUMENTS}


def date_time(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def numeric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def parse_scan(payload, now):
    """Match exact identifiers; never rely on response order or infer a date."""
    quotes, errors, seen = {}, {}, set()
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('Réponse scanner non conforme')
    for row in payload['data']:
        if not isinstance(row,dict): continue
        ticker = row.get('s')
        if ticker not in CONTRACTS:
            continue
        if ticker in seen:
            quotes.pop(ticker, None)
            errors[ticker] = 'Identifiant dupliqué dans la réponse'
            continue
        seen.add(ticker)
        data = row.get('d')
        if not isinstance(data, list) or len(data) != len(COLUMNS):
            errors[ticker] = 'Colonnes source incomplètes'
            continue
        description, price, change, currency, timestamp, mode = data
        try:
            ts = numeric(timestamp)
            dt = datetime.fromtimestamp(ts, timezone.utc) if ts is not None and ts > 0 else None
        except (ValueError, OverflowError, OSError):
            dt = None
        expected_currency = CONTRACTS[ticker][4]
        if (numeric(price) is None or price <= 0 or dt is None or dt > now
                or expected_currency and currency != expected_currency
                or change is not None and numeric(change) is None):
            errors[ticker] = 'Valeur, unité ou horodatage non admissible'
            continue
        quotes[ticker] = dict(ticker=ticker, value=price, change_pct=change,
            observed_at=dt.isoformat(), currency=currency, mode=str(mode or 'non renseigné')[:60],
            description=str(description or '')[:120], source='TradingView — scanner public',
            source_url='https://www.tradingview.com/symbols/'+ticker.replace(':', '-')+'/',
            collected_at=now.isoformat())
    return quotes, errors


def fetch_scan(timeout=20):
    request = Request(SCANNER, data=json.dumps(dict(symbols=dict(tickers=list(CONTRACTS),
        query=dict(types=[])), columns=COLUMNS)).encode(), headers={
        'User-Agent':'BVCAnalyzerNour/1.0', 'Content-Type':'application/json'})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(2_000_000))


def merge_snapshot(previous, fresh, errors, now):
    quotes, issues = {}, dict(errors)
    for ticker in CONTRACTS:
        old = (previous.get('quotes') or {}).get(ticker)
        new = fresh.get(ticker)
        if old and new:
            old_date, new_date = date_time(old.get('observed_at')), date_time(new.get('observed_at'))
            if old_date and (new_date < old_date or new_date == old_date and (
                    new['value'] != old.get('value') or new['change_pct'] != old.get('change_pct'))):
                issues[ticker] = 'Régression ou contradiction au même horodatage ; archive conservée'
                new = None
        if new:
            quotes[ticker] = {**new, 'collection_state':'collected'}
        elif old:
            quotes[ticker] = {**old, 'collection_state':'cached'}
        else:
            issues.setdefault(ticker, 'Observation absente')
    return dict(schema_version=1, checked_at=now.isoformat(), quotes=quotes, errors=issues,
        status='ok' if len(quotes)==12 and not issues and len(fresh)==12 else 'partial' if fresh else 'failed',
        role='Contexte uniquement : aucune contribution aux scores, aucune prédiction')


def context_view(snapshot, cutoff):
    """No observation later than the requested instant, including archived briefs."""
    groups = {}
    for ticker, name, group, unit, currency in INSTRUMENTS:
        raw = (snapshot.get('quotes') or {}).get(ticker) or {}
        dt = date_time(raw.get('observed_at'))
        admissible = (dt is not None and dt <= cutoff and numeric(raw.get('value')) is not None
                      and raw['value'] > 0 and (currency is None or raw.get('currency') == currency))
        item = dict(ticker=ticker, name=name, unit=unit, value=None, change_pct=None,
                    state='unavailable', notice='Observation indisponible à cette date')
        if admissible:
            item.update(raw)
            item['change_pct'] = numeric(raw.get('change_pct'))
            item['state'] = 'cached' if raw.get('collection_state') == 'cached' else 'observed'
            item['notice'] = 'Archive conservée après collecte incomplète' if item['state']=='cached' else 'Dernière observation source'
        elif dt and dt > cutoff:
            item['notice'] = 'Observation postérieure à la date limite : écartée'
        if not admissible and not dt:
            item['notice'] = snapshot.get('errors',{}).get(ticker,item['notice'])
        groups.setdefault(group, []).append(item)
    return dict(schema_version=1, cutoff=cutoff.isoformat(), checked_at=snapshot.get('checked_at'),
        status=snapshot.get('status', 'not_observed'), groups=[dict(title=k, rows=v) for k,v in groups.items()],
        errors=snapshot.get('errors', {}), role='Contexte seulement ; NLP 0 %, aucun impact sur les scores')


def mode_label(mode):
    if mode == 'streaming':
        return 'Flux source « streaming » ; affichage par instantanés'
    if str(mode).startswith('delayed_streaming_'):
        try: return f'Différé source : {int(mode.rsplit("_",1)[1]) // 60} min'
        except ValueError: pass
    return 'Mode source : '+str(mode or 'non renseigné')
