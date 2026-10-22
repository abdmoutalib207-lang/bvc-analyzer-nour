"""Publication view of a dated reconciliation bound to the exact canonical file."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlsplit
from .market import CASABLANCA


def validated_primary_scope(report, audit):
    """A fresh, exact primary proof may be published, never called multisource.

    No corrections, source conflicts, stale proof, incomplete universe or
    aggregate mismatch qualify. The secondary observation remains unusable.
    """
    def number(value):
        if isinstance(value, bool):
            raise ValueError('boolean')
        result=Decimal(str(value))
        if not result.is_finite() or result<0:
            raise ValueError('number')
        return result
    try:
        if (audit.get('status')!='primary_checked' or audit.get('publication_scope')!='primary_only'
                or any(audit.get(k) is not True for k in ('publication_safe','internal_match','aggregate_match'))
                or any(audit.get(k) is not False for k in ('cross_source_verified','quantities_cross_source_verified'))
                or audit.get('corrections') or audit.get('proposed_corrections') or audit.get('refusals')
                or audit.get('secondary_status') not in ('invalid','unavailable','error','timeout')):
            return False
        overview=report['market_overview'];session=overview['asof']
        snapshot=report['provenance']['market_snapshot_sha256']
        observed=datetime.fromisoformat(audit['observed_at'].replace('Z','+00:00'))
        local_observed=observed.astimezone(CASABLANCA) if observed.tzinfo else observed
        if (overview.get('status')!='closed' or overview.get('provisional') is True
                or not snapshot or len(snapshot)!=64 or audit.get('validated_snapshot_sha256')!=snapshot
                or audit.get('session')!=session or date.fromisoformat(session).weekday()>=5
                or observed.tzinfo is None or local_observed.date()<date.fromisoformat(session)
                or local_observed.date().isoformat()>report['analysis_date']
                or (local_observed.date().isoformat()==session and local_observed.hour<16)):
            return False
        providers=audit['providers']
        if (len(providers)!=2 or urlsplit(providers[0]['source_url']).hostname!='www.cdgcapitalbourse.ma'
                or urlsplit(providers[0]['source_url']).scheme!='https'
                or providers[1].get('status')!=audit['secondary_status']
                or any(len(p.get('raw_sha256',''))!=64 for p in providers)):
            return False
        rows=[r for r in report['results'] if r.get('asof')==session and
              (number(r.get('day_shares',0))>0 or number(r.get('day_turnover_mad_actual',0))>0)]
        symbols=[r['symbol'] for r in rows];proof=audit['validated_lines']
        if (not rows or len(symbols)!=len(set(symbols)) or sorted(symbols)!=audit['validated_symbols']
                or set(proof)!=set(symbols)):
            return False
        amount=Decimal(0);shares=Decimal(0)
        for row in rows:
            line=proof[row['symbol']]
            if any(number(line[k])!=number(row[f]) for k,f in
                   (('price','price'),('shares','day_shares'),('turnover_mad','day_turnover_mad_actual'))):
                return False
            q=number(line['shares'])
            if q<=0 or q!=q.to_integral_value() or number(line['price'])<=0:
                return False
            amount+=number(line['turnover_mad']);shares+=q
        for key in ('cdg_lines','retained_before','retained_after','cdg_overview'):
            total=audit['totals'][key]
            if (abs(number(total['turnover_mad'])-amount)>Decimal('.01')
                    or number(total['shares'])!=shares or number(total['quoted'])!=len(rows)):
                return False
        return (abs(number(overview['turnover_mad'])-amount)<=Decimal('.01')
                and number(overview['shares'])==shares and number(overview['breadth']['quoted'])==len(rows))
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return False


def validated_detail_scope(report, audit):
    """Permit only an exact dated two-provider title proof, never its global total."""
    def numeric(value):
        if isinstance(value, bool):
            raise ValueError('boolean')
        number=Decimal(str(value))
        if not number.is_finite() or number<0:
            raise ValueError('invalid number')
        return number
    try:
        if (audit.get('status')!='detail_matched' or audit.get('publication_scope')!='validated_title_lines'
                or audit.get('aggregate_match') is not False
                or audit.get('corrections') or audit.get('proposed_corrections')
                or any(audit.get(k) is not True for k in ('publication_safe','internal_match','cross_source_verified','quantities_cross_source_verified'))):
            return False
        overview=report['market_overview'];session=overview['asof']
        snapshot=report['provenance']['market_snapshot_sha256']
        if not snapshot or len(snapshot)!=64 or audit.get('validated_snapshot_sha256')!=snapshot or audit.get('session')!=session:
            return False
        hosts=set()
        for provider in audit['providers']:
            url=urlsplit(provider['source_url'])
            if url.scheme=='https' and url.hostname and not url.username and not url.password and len(provider.get('raw_sha256',''))==64:
                hosts.add(url.hostname)
        if len(hosts)<2:
            return False
        rows=[r for r in report['results'] if r.get('asof')==session and
              (numeric(r.get('day_shares',0))>0 or numeric(r.get('day_turnover_mad_actual',0))>0)]
        symbols=[r['symbol'] for r in rows]
        proof=audit['validated_lines']
        if not rows or len(symbols)!=len(set(symbols)) or sorted(symbols)!=audit['validated_symbols'] or set(proof)!=set(symbols):
            return False
        amount=Decimal(0);shares=Decimal(0)
        for row in rows:
            line=proof[row['symbol']]
            for key, field in (('shares','day_shares'),('turnover_mad','day_turnover_mad_actual'),('price','price')):
                if numeric(line[key])!=numeric(row[field]):
                    return False
            quantity=numeric(line['shares'])
            if quantity!=quantity.to_integral_value() or quantity<=0 or numeric(line['price'])<=0:
                return False
            amount+=numeric(line['turnover_mad']);shares+=quantity
        for key in ('cdg_lines','secondary','retained_after'):
            total=audit['totals'][key]
            if numeric(total['turnover_mad'])!=amount or numeric(total['shares'])!=shares or numeric(total['quoted'])!=len(rows):
                return False
        if audit['totals']['secondary'].get('quantity_rows')!=len(rows):
            return False
        announced=audit['totals']['cdg_overview']
        if (numeric(announced['turnover_mad'])!=numeric(overview['turnover_mad'])
                or numeric(announced['shares'])!=numeric(overview['shares'])
                or numeric(announced['quoted'])!=numeric(overview['breadth']['quoted'])):
            return False
        return (amount!=numeric(announced['turnover_mad']) or shares!=numeric(announced['shares']) or len(rows)!=numeric(announced['quoted']))
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return False


def visible_integrity(audit,report):
    result=deepcopy(audit or {'status':'not_observed','cross_source_verified':False})
    current=(report.get('market_overview') or {}).get('asof')
    snapshot=(report.get('provenance') or {}).get('market_snapshot_sha256')
    claimed = result.get('status') in ('matched','reconciled') or result.get('cross_source_verified')
    if claimed and (result.get('session')!=current or result.get('validated_snapshot_sha256')!=snapshot
            or result.get('publication_safe') is not True or result.get('internal_match') is not True
            or result.get('cross_source_verified') is not True):
        result.update(status='stale',cross_source_verified=False,quantities_cross_source_verified=False,
                      publication_safe=False,notice='Le contrôle conservé ne correspond pas à cette version de la séance ; nouvelle vérification requise.')
    if result.get('publication_scope')=='validated_title_lines' and not validated_detail_scope(report,result):
        result.update(status='stale',cross_source_verified=False,quantities_cross_source_verified=False,publication_safe=False,
                      notice='Preuve des lignes détaillées incomplète ou différente du rapport ; publication refusée.')
    if result.get('publication_scope')=='primary_only' and not validated_primary_scope(report,result):
        result.update(status='stale',publication_safe=False,
                      notice='Preuve de la source principale différente du rapport ; publication refusée.')
    return result


def memory_summary(memory):
    entries=list((memory or {}).get('entries',{}).values())
    return {'incidents':len(entries),'open':sum(r.get('status')=='open' for r in entries),
            'resolved':sum(r.get('status')=='resolved' for r in entries),
            'lessons':len((memory or {}).get('lessons',{})),
            'last_update':(memory or {}).get('updated_at'),'url':'error-memory.json',
            'lessons_catalog':[{k:lesson.get(k) for k in ('id','title','rule')}
                              for lesson in (memory or {}).get('lessons',{}).values()]}


def integrity_summary(audit):
    result={k:deepcopy((audit or {}).get(k)) for k in ('status','session','observed_at',
        'publication_safe','internal_match','cross_source_verified','quantities_cross_source_verified',
        'providers','notices','notice','publication_scope','aggregate_match','secondary_status')}
    result['totals']={k:deepcopy((audit or {}).get('totals',{}).get(k)) for k in ('cdg_overview','cdg_lines','secondary','retained_after')}
    return result
