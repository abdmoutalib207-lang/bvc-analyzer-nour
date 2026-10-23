"""Local quarantine is explicit; registry/security/publication failures stay global."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import re


class GlobalIntegrityError(ValueError):
    pass


def validate_fixture(fixture, registry=None):
    if not isinstance(fixture, dict) or not isinstance(fixture.get('records'), dict):
        raise GlobalIntegrityError('Schéma global des sociétés invalide')
    symbols = fixture.get('symbols')
    if (not isinstance(symbols, list) or not symbols or len(set(symbols)) != len(symbols)
            or any(not isinstance(s, str) or not re.fullmatch(r'[A-Z0-9]{2,5}', s) for s in symbols)
            or set(fixture['records']) - set(symbols)):
        raise GlobalIntegrityError('Référentiel de sociétés invalide ou dupliqué')
    if registry is not None and (set(symbols) != set(registry)
            or len(set(registry.values())) != len(registry)):
        raise GlobalIntegrityError('Référentiel des codes officiels incohérent')
    for symbol, record in fixture['records'].items():
        if not isinstance(record, dict) or record.get('symbol') != symbol:
            raise GlobalIntegrityError('Identité de société contradictoire : '+symbol)
    date.fromisoformat(str(fixture.get('snapshot_updated', ''))[:10])
    return True


def issue(item, domain, code, reason, metrics=(), source=None, evidence=None):
    state = item.setdefault('resilience', {'state':'healthy', 'suspended':{}, 'anomalies':[]})
    state['state'] = 'degraded'
    entry = dict(symbol=item['symbol'], domain=domain, code=code, reason=reason,
                 severity='blocking_local', metrics=list(metrics), source=source,
                 action='Conserver les autres calculs ; rapprocher les données ou corriger ce calcul.')
    if evidence is not None:
        entry['evidence'] = deepcopy(evidence)
    if entry not in state['anomalies']:
        state['anomalies'].append(entry)
    for metric in metrics:
        state['suspended'][metric] = {'code':code, 'reason':reason}
    return entry


def guarded(item, domain, function, fallback):
    try:
        return function()
    except (GlobalIntegrityError, MemoryError):
        raise
    except Exception as exc:
        issue(item, domain, 'calculation_exception',
              f'Calcul {domain} interrompu ({type(exc).__name__} : {str(exc)[:240]}) ; sortie suspendue.', [domain])
        return fallback()


def _get(row, path):
    value = row
    for part in path.split('.'):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def health_with_quarantines(audit, report, kind='calculations'):
    """Keep the independent failures; accept only explicitly absent local outputs.

    The raw oracle is unchanged. A claimed quarantine never accepts an erroneous
    numeric value. Universe, unknown metric and unresolved positive output fail.
    """
    out = deepcopy(audit)
    rows = {r['symbol']:r for r in report['results']}
    remaining, quarantined = [], []
    for failure in audit.get('failures', []):
        row = rows.get(failure.get('symbol'))
        metric = failure.get('metric', '')
        path = ('fundamental.evidence.'+metric[5:] if kind=='financial' and metric.startswith('unit:') else 'canonical_score.value' if metric == 'score' else 'fundamental.'+metric
                if kind == 'financial' else metric.replace('statistics.', 'historical_statistics.', 1))
        state = (row or {}).get('resilience') or {}
        suspended = state.get('suspended') or {}
        domain = 'historical_statistics' if metric.startswith('statistics.') else path.split('.')[0]
        covered = path in suspended or domain in suspended
        absent = _get(row or {}, path) is None
        if metric.startswith('statistics.'):
            stats = (row or {}).get('historical_statistics') or {}
            absent = stats.get('status') == 'unavailable' and stats.get('horizons') == []
        if row and covered and absent and metric not in ('symbols', 'nlp_weight'):
            quarantined.append(failure)
        else:
            remaining.append(failure)
    out['failures'] = remaining
    out['quarantined_failures'] = quarantined
    degraded = quarantined or any(r.get('resilience',{}).get('anomalies') for r in report['results'])
    out['status'] = 'blocked' if remaining else 'degraded' if degraded else audit.get('status')
    out['quarantined_assertions'] = len(quarantined)
    return out


def isolate_audit_failures(report, audit, kind='calculations'):
    from .analytics import canonical_score
    from .financial_audit import METRICS
    rows = {r['symbol']:r for r in report['results']}
    for failure in audit.get('failures', []):
        symbol, metric = failure.get('symbol'), failure.get('metric', '')
        if symbol not in rows:
            raise GlobalIntegrityError('Univers du contrôle indépendant incohérent')
        row = rows[symbol]
        if kind == 'financial':
            if metric == 'score':
                path = 'canonical_score.value'
                row['canonical_score'].update(value=None, state='NON_CALCULABLE')
            elif metric.startswith('unit:'):
                field=metric[5:];path='fundamental.evidence.'+field
                fact=row['fundamental']['evidence'].pop(field,None)
                row['fundamental'].setdefault('quarantined_evidence',{})[field]=fact
                affected={m for c in row['fundamental']['financial_audit'].get('checks',[]) if field in c.get('fields',[]) for m in c.get('blocked_metrics',[])}
                for m in affected:row['fundamental'][m]=None
            elif metric in METRICS:
                path = 'fundamental.'+metric
                row['fundamental'][metric] = None
                row['fundamental']['metric_availability'][metric] = dict(
                    status='blocked', reason_codes=['independent_arithmetic_mismatch'])
                blocked = row['fundamental']['financial_audit']['blocked_metrics']
                if metric not in blocked:
                    blocked.append(metric); blocked.sort()
                row['fundamental']['financial_audit']['status'] = 'blocked'
                row['fundamental']['coverage_pct'] = 25*sum(row['fundamental'].get(k) is not None
                    for k in ('eps_mad','pb','roe_pct','revenue_growth_pct'))
            else:
                raise GlobalIntegrityError('Contrat financier global invalide : '+metric)
        elif metric.startswith('technical.') and metric.count('.') == 1:
            path = metric
            row['technical'][metric.split('.')[1]] = None
        elif metric.startswith('liquidity.'):
            path = metric
            row['liquidity'][metric.split('.')[1]] = None
            row['liquidity'].update(ready=False, capacity_shares_per_session_at_10pct=None,
                                    exit_days_at_10pct=None)
        elif metric.startswith('statistics.'):
            path = 'historical_statistics'
            row['historical_statistics'] = dict(status='unavailable', horizons=[],
                reason='Statistiques suspendues après divergence indépendante.')
        else:
            raise GlobalIntegrityError('Contrat global de calcul invalide : '+metric)
        issue(row, path.split('.')[0], 'independent_arithmetic_mismatch',
              'Divergence du recalcul indépendant ; indicateur suspendu.', [path], evidence=failure)
        if metric != 'score':
            row['canonical_score'] = canonical_score(row, row['technical'], row['fundamental'])
    return report


def update_last_healthy(previous, report, checked_at):
    out = deepcopy(previous or {'schema_version':1, 'issuers':{}})
    for row in report['results']:
        old = out['issuers'].get(row['symbol'])
        row['last_validated_at'] = checked_at if not row.get('resilience', {}).get('anomalies') else None
        if old:
            row['last_healthy'] = {k:old.get(k) for k in ('asof','validated_at','sha256')}
        if row.get('resilience', {}).get('anomalies') or row['decision'] in ('INDISPONIBLE','SUSPENDU'):
            continue
        snapshot = {k:deepcopy(row[k]) for k in ('symbol','asof','price','technical','fundamental','liquidity')}
        out['issuers'][row['symbol']] = dict(asof=row['asof'], validated_at=checked_at, data=snapshot,
            sha256=sha256(json.dumps(snapshot,sort_keys=True,allow_nan=False).encode()).hexdigest())
    proof=deepcopy(report.get('cross_source_volume_audit') or {})
    proof=proof.get('last_valid_proof') or proof
    if proof.get('publication_safe'):
        out['market']={'snapshot_sha256':report.get('provenance',{}).get('market_snapshot_sha256'),
            'overview':deepcopy(report.get('market_overview') or {}),'proof':proof,'built_at':checked_at}
    return out


def retained_market_context(snapshot_sha256, cache, health):
    """Restore a dated market context only when the canonical file is unchanged."""
    prior=(cache or {}).get('market') or {}
    proof=prior.get('proof') or {}
    if (health.get('result')!='error' or prior.get('snapshot_sha256')!=snapshot_sha256
            or not snapshot_sha256 or proof.get('validated_snapshot_sha256')!=snapshot_sha256
            or proof.get('status') not in ('matched','reconciled','primary_checked','detail_matched','partial')
            or proof.get('publication_safe') is not True
            or proof.get('session')!=(prior.get('overview') or {}).get('asof')):
        return None
    return deepcopy(prior)
