"""Publication view of a dated reconciliation bound to the exact canonical file."""
from copy import deepcopy


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
        'providers','notices','notice')}
    result['totals']={k:deepcopy((audit or {}).get('totals',{}).get(k)) for k in ('cdg_overview','secondary','retained_after')}
    return result
