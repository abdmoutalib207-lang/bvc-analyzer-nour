"""Exact per-issuer proofs for a partial market; never certify its aggregate."""
from copy import deepcopy
from datetime import datetime, date
from decimal import Decimal
import hashlib
from urllib.parse import urlsplit

from .market import normalized_quote, session_date, CASABLANCA, SOURCE_URL


def number(value):
    if isinstance(value, bool):
        raise ValueError('boolean')
    n = Decimal(str(value))
    if not n.is_finite() or n < 0:
        raise ValueError('number')
    return n


def isolate_market_lines(fixture, lines, overview, secondary, codes, now, minimum=20):
    """No revision of a disputed line; independent healthy lines may proceed."""
    session = overview['asof']
    if (overview.get('status') != 'closed' or overview.get('provisional') is True
            or date.fromisoformat(session).weekday() >= 5 or session > now.date().isoformat()
            or (session == now.date().isoformat() and now.hour < 16)
            or not isinstance(lines, list) or len(set(codes.values())) != len(codes)):
        raise ValueError('Global market contract invalid')
    inverse = {v:k for k,v in codes.items()}
    candidates, rejected, seen = {}, {}, set()
    def reject(s, reason, observed=None):
        rejected[s] = {'symbol':s,'session':session,'domain':'volume','code':'market_line_quarantined',
            'reason':reason,'source':SOURCE_URL,'observed_at':now.isoformat(),
            'resolution':'pending_review','observed':observed or {}}
        candidates.pop(s,None)
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError('Global source schema invalid')
        code = str(line.get('Symbol') or '').strip().upper()
        s = inverse.get(code)
        if s is None:
            if line.get('QteEchangee') not in (None,'',0,'0'):
                raise ValueError('Traded issuer absent from registry')
            continue
        if s in seen:
            reject(s,'Lignes primaires dupliquées pour ce titre'); continue
        seen.add(s)
        try:
            day = session_date(line.get('DateDernierCours'))
            shares = number(line.get('QteEchangee') or 0)
            if day != session or shares == 0:
                if day and day > session and shares > 0:
                    reject(s,'Date primaire future ou postérieure à la séance')
                continue
            q = normalized_quote(line,s)
            if q is None or line.get('provisional') is True:
                raise ValueError('Cotation non définitive')
            candidates[s] = q['bar']
        except (ValueError, TypeError, ArithmeticError):
            reject(s,'Cours, quantité ou volume primaire invalide',
                   {k:line.get(k) for k in ('Cours','Volumes','QteEchangee','DateDernierCours')})
    secondary_ok = False
    other = {}
    if isinstance(secondary,dict) and secondary.get('status') == 'ok':
        stamp = datetime.fromisoformat(str(secondary.get('observed_at')))
        host = urlsplit(str(secondary.get('source_url') or ''))
        secondary_ok = bool(secondary.get('session') == session and secondary.get('scope') == 'cash_equities'
            and secondary.get('market_closed') is True and secondary.get('provisional') is not True
            and stamp.tzinfo and stamp <= now and stamp.astimezone(CASABLANCA).date().isoformat() >= session
            and (stamp.astimezone(CASABLANCA).date().isoformat() != session or stamp.astimezone(CASABLANCA).hour >= 16)
            and host.scheme == 'https' and host.hostname and 'cdg' not in host.hostname.lower()
            and 'cdg' not in str(secondary.get('original_provider') or secondary.get('provider') or '').lower())
        if secondary_ok:
            for r in secondary.get('rows') or []:
                if not isinstance(r,dict):
                    raise ValueError('Global secondary schema invalid')
                s = inverse.get(str(r.get('symbol') or '').strip().upper())
                if not s:
                    raise ValueError('Unknown secondary issuer')
                if s in other:
                    reject(s,'Lignes secondaires dupliquées'); continue
                other[s] = r
    out = deepcopy(fixture)
    proof = {}
    for s, bar in list(candidates.items()):
        rec = out['records'].get(s) or {}
        try:
            previous=rec.get('quarantined_market')
            if previous and (previous.get('session')!=session or not secondary_ok):
                raise ValueError('Contradiction historique ou multisource non résolue')
            old = next(b for b in rec.get('candles',[]) if b.get('d') == session)
            if (rec.get('price_asof') != session or number(rec.get('price')) != number(bar['c'])
                    or any(number(old.get(k)) != number(bar[k]) for k in ('o','h','l','c','v'))
                    or number(rec.get('day_shares')) != number(bar['v'])
                    or abs(number(rec.get('day_turnover_mad'))-number(bar['turnover_mad'])) > Decimal('.01')):
                raise ValueError('Stored row differs from primary observation')
            if secondary_ok:
                r = other.get(s)
                if (not r or r.get('session') != session or number(r.get('price')) != number(bar['c'])
                        or abs(number(r.get('amount_mad'))-number(bar['turnover_mad'])) > Decimal('.01')
                        or (r.get('shares') is not None and number(r['shares']) != number(bar['v']))):
                    raise ValueError('Secondary line contradicts primary or is missing')
            proof[s] = {'price':str(bar['c']),'shares':int(bar['v']),
                        'turnover_mad':str(bar['turnover_mad'])}
        except (ValueError, TypeError, ArithmeticError, StopIteration, KeyError):
            reject(s,'Cotation ou volume non rapproché ; aucune source choisie arbitrairement',
                   {'primary':bar,'secondary':other.get(s)})
    for s,rec in out['records'].items():
        if rec.get('price_asof') == session and rec.get('day_shares') and s not in proof:
            rejected.setdefault(s,{'symbol':s,'session':session,'domain':'source','code':'missing_primary_line',
                'reason':'Ligne courante sans preuve primaire exploitable','source':SOURCE_URL,
                'observed_at':now.isoformat(),'resolution':'pending_review'})
    if len(proof) < minimum:
        raise ValueError('No sufficient independently usable title set')
    for s in proof:
        out['records'][s].pop('quarantined_market',None)
    for s,problem in rejected.items():
        out['records'][s]['quarantined_market'] = problem
    audit = dict(schema_version=1, observed_at=now.isoformat(),session=session,status='partial',
        publication_scope='isolated_issuer_lines', publication_safe=True, internal_match=False,
        aggregate_match=False,cross_source_verified=False,quantities_cross_source_verified=False,
        validated_symbols=sorted(proof), validated_lines=proof, quarantined_symbols=sorted(rejected),
        corrections=[],refusals=list(rejected.values()), totals={},
        providers=[{'provider':'CDG Capital Bourse','source_url':SOURCE_URL}],
        notices=['Publication partielle par société ; aucun agrégat global ni validation multisource globale attesté.',
                 'Titres en conflit isolés ; dernière valeur saine distincte, jamais présentée comme cotation actuelle.'])
    if isinstance(secondary,dict):
        audit['providers'].append({k:secondary.get(k) for k in ('provider','source_url','status')})
    return out,audit


def validated_local_scope(report, audit):
    try:
        if (audit.get('status') != 'partial' or audit.get('publication_scope') != 'isolated_issuer_lines'
                or audit.get('publication_safe') is not True or audit.get('aggregate_match') is not False
                or audit.get('cross_source_verified') is not False or audit.get('corrections')
                or audit.get('validated_snapshot_sha256') != report['provenance']['market_snapshot_sha256']
                or not report['provenance']['market_snapshot_sha256']):
            return False
        session = audit['session']
        if session != report['market_overview']['asof'] or session > report['analysis_date']:
            return False
        stamp = datetime.fromisoformat(audit['observed_at'])
        if (not stamp.tzinfo or stamp.astimezone(CASABLANCA).date().isoformat() < session
                or stamp.astimezone(CASABLANCA).date().isoformat() > report['analysis_date']):
            return False
        provider = audit['providers'][0]
        if urlsplit(provider['source_url']).hostname != 'www.cdgcapitalbourse.ma' or len(provider.get('raw_sha256','')) != 64:
            return False
        rows = {r['symbol']:r for r in report['results']}
        if len(rows) != len(report['results']):
            return False
        proof = audit['validated_lines']; isolated = set(audit['quarantined_symbols'])
        if not proof or set(proof) != set(audit['validated_symbols']) or set(proof) & isolated or not isolated <= set(rows):
            return False
        for s,p in proof.items():
            r = rows[s]
            q=number(p['shares'])
            if q<=0 or q!=q.to_integral_value() or number(p['price'])<=0:return False
            if r.get('asof') != session or any(number(p[k]) != number(r[field]) for k,field in
                [('price','price'),('shares','day_shares'),('turnover_mad','day_turnover_mad_actual')]):
                return False
        for s,r in rows.items():
            if s in isolated:
                if any(r.get(k) is not None for k in ('price','day_shares','day_turnover_mad_actual')):
                    return False
                if not r.get('resilience',{}).get('suspended',{}).get('market'):
                    return False
            elif r.get('asof') == session and r.get('day_shares') and s not in proof:
                return False
        return True
    except (ValueError, TypeError, KeyError, ArithmeticError):
        return False
