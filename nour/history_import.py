"""Reconcile documented operator-export histories, without importing any score.

The source repository is read only. A manifest authorizes the historical window;
observations after that window never replace Nour's existing daily observations.
"""
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

KEYS=('o','h','l','c','v')
CANCELLED={'2026-09-17'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def valid_bar(bar,asof):
    try:
        day=date.fromisoformat(bar['d'])
        return (day.isoformat()<=asof and day.weekday()<5 and bar['d'] not in CANCELLED
            and all(isinstance(bar.get(k),(int,float)) and not isinstance(bar[k],bool) and math.isfinite(bar[k]) for k in KEYS)
            and min(bar[k] for k in ('o','h','l','c'))>0 and bar['l']<=min(bar['o'],bar['c'])<=max(bar['o'],bar['c'])<=bar['h']
            and bar['v']>=0 and float(bar['v']).is_integer())
    except (KeyError,TypeError,ValueError):
        return False


def reconcile(fixture,source,code_map,asof,source_commit,base_commit):
    """Return a new fixture plus a reproducible, per-issuer reconciliation log."""
    if not re.fullmatch('[a-f0-9]{40}',source_commit) or not re.fullmatch('[a-f0-9]{40}',base_commit):
        raise ValueError('Exact source and previous Nour commits are required')
    source=Path(source);updated=deepcopy(fixture);details=[]
    for symbol in fixture['symbols']:
        path=source/'pipeline/candles'/f'{symbol}.json'
        manifest_path=source/'datasets/historiques_importes'/f'{symbol}.json'
        if not path.exists() or not manifest_path.exists():
            details.append(dict(symbol=symbol,status='no_operator_manifest_no_replacement'))
            continue
        raw=json.loads(path.read_text());manifest=json.loads(manifest_path.read_text())
        if (manifest.get('ticker')!=symbol or manifest.get('code_operateur')!=code_map.get(symbol)
                or not re.fullmatch('[a-f0-9]{64}',manifest.get('sha256_fichier_recu',''))
                or not isinstance(raw,list)):
            raise ValueError(f'{symbol}: operator identity or manifest hash mismatch')
        period=manifest.get('periode_source') or manifest.get('periode') or []
        if len(period)!=2 or any(date.fromisoformat(d).isoformat()!=d for d in period) or period[0]>period[1] or period[1]>asof:
            raise ValueError(f'{symbol}: invalid or future export period')
        record=updated['records'][symbol];original=fixture['records'][symbol]['candles']
        if not raw:
            details.append(dict(symbol=symbol,status='documented_no_transactions',period=period,operator_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest()))
            continue
        if len({b.get('d') for b in raw})!=len(raw):
            raise ValueError(f'{symbol}: duplicate source dates')
        old={b['d']:deepcopy(b) for b in original};merged=deepcopy(old)
        candidate={b['d']:{'d':b['d'],**{k:b[k] for k in KEYS}} for b in raw if valid_bar(b,asof)}
        invalid_dates={b.get('d') for b in raw if not valid_bar(b,asof)}
        field_changes=Counter();replaced=[];added=[];removed=[];recent=[]
        for day in sorted(old):
            if period[0]<=day<=period[1] and day not in candidate and day not in invalid_dates:
                removed.append(day);del merged[day]
        for day,bar in candidate.items():
            in_export=period[0]<=day<=period[1]
            if day in old:
                fields=[k for k in KEYS if old[day].get(k)!=bar[k]]
                if fields and in_export:
                    replaced.append(day);field_changes.update(fields);merged[day]=bar
                elif fields and day>period[1]:
                    recent.append(dict(session=day,fields=fields,retained={k:old[day].get(k) for k in fields},observed={k:bar[k] for k in fields},resolution='retained_nour_daily_observation'))
            elif in_export or day>period[1] and bar['v']>0:
                merged[day]=bar;added.append(day)
        record['candles']=[merged[d] for d in sorted(merged)]
        record['full_history_count_reported']=len(record['candles'])
        quote_alignment = None
        last = record['candles'][-1] if record['candles'] else None
        old_quote_date = record.get('price_asof')
        if (last and isinstance(old_quote_date, str) and old_quote_date < last['d']
                and last['d'] in candidate and (last['d'] <= period[1] or last['v'] > 0)):
            quote_alignment = {'previous_date': old_quote_date, 'previous_price': record.get('price'),
                               'date': last['d'], 'price': last['c'],
                               'source': 'documented_operator_export' if last['d'] <= period[1] else 'pinned_principal_daily_observation'}
            record.update(price=last['c'], price_asof=last['d'],
                price_source=('Bourse de Casablanca · export opérateur rapproché' if last['d'] <= period[1]
                              else 'Archive principale figée · observation datée'),
                day_shares=last['v'], day_turnover_mad=None)
        imported=bool(added or removed or replaced)
        if imported:
            record['history_provenance']={
                'method':'operator_export_manifest_over_legacy_window_v1','source_commit':source_commit,
                'source_url':f'https://github.com/abdmoutalib207-lang/-bvc-analyzer/blob/{source_commit}/pipeline/candles/{symbol}.json',
                'operator_export_sha256':manifest['sha256_fichier_recu'],'operator_period':period,
                'source_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'manifest_url':f'https://github.com/abdmoutalib207-lang/-bvc-analyzer/blob/{source_commit}/datasets/historiques_importes/{symbol}.json',
                'reconciled_asof':asof,'added':len(added),'replaced':len(replaced),'removed':len(removed),
                'notice':'Export opérateur documenté prioritaire sur l’ancienne archive dans sa période. Zéros de quantité conservés lorsqu’ils figurent dans l’export ; aucun trou interpolé. Observations récentes Nour conservées.'}
        details.append(dict(symbol=symbol,status='reconciled' if imported else 'already_matching',period=period,
            before=len(original),after=len(record['candles']),added=len(added),replaced=len(replaced),removed=len(removed),
            replaced_fields=dict(field_changes),replaced_dates=replaced,added_dates=added,removed_dates=removed,
            source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),operator_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            operator_export_sha256=manifest['sha256_fichier_recu'],before_sha256=digest(original),after_sha256=digest(record['candles']),
            rejected_source_dates=sorted(d for d in invalid_dates if isinstance(d,str)),recent_observations_retained=recent))
        details[-1]['quote_alignment'] = quote_alignment
    audit=dict(version='nour-history-reconciliation-v1',asof=asof,source_commit=source_commit,previous_nour_commit=base_commit,
        policy='Documented operator export replaces the legacy window. No scores/fundamentals imported. Existing observations after each export period are retained.',
        issuers=details,changed_issuers=sum(r['status']=='reconciled' for r in details),
        added=sum(r.get('added',0) for r in details),replaced=sum(r.get('replaced',0) for r in details),removed=sum(r.get('removed',0) for r in details))
    return updated,audit
