"""Corroborate closing volumes before publication; preserve incident evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nour.market import CASABLANCA, SOURCE_URL, atomic_json, fetch_cdg
from nour.secondary_market import fetch_wafabourse
from nour.volume_guard import reconcile_volumes
from nour.error_memory import update_error_memory, record_lesson


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else deepcopy(default)


def persist_result(data, fixture, candidate, audit):
    """Commit only a validated candidate; archive before/after evidence separately."""
    path = data/'market_snapshot.json'
    audit['previous_snapshot_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    if audit.get('publication_safe') and candidate != fixture:
        atomic_json(path, candidate)
    audit['canonical_snapshot_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    audit['validated_snapshot_sha256'] = audit['canonical_snapshot_sha256'] if audit.get('publication_safe') else None
    health = load(data/'health.json', {})
    resolved, remaining = [], []
    for conflict in (health.get('details') or {}).get('conflicts') or []:
        rec = candidate['records'].get(conflict.get('symbol'), {})
        bar = next((b for b in rec.get('candles', []) if b.get('d') == conflict.get('session')), {})
        if (audit.get('publication_safe') and audit.get('cross_source_verified')
                and conflict.get('session') == audit.get('session')
                and conflict.get('symbol') in (audit.get('validated_symbols') or [])
                and bool(conflict.get('observed'))
                and set(conflict['observed']) == set(conflict.get('fields') or [])
                and set(conflict['observed']) <= set(audit.get('validated_fields') or [])
                and all(bar.get(k) == v for k,v in (conflict.get('observed') or {}).items())):
            resolved.append({**conflict, 'resolution':'corroborated_by_cdg_wafabourse',
                             'resolved_at':audit['observed_at']})
        else:
            remaining.append(conflict)
    audit['resolved_conflicts'] = resolved
    if resolved or audit.get('corrections'):
        health.update(checked_at=audit['observed_at'],last_session=audit['session'],
            result='partial' if remaining else 'reconciled',
            message=f"{len(audit.get('corrections') or [])} volumes rapprochés entre fournisseurs ; {len(remaining)} conflit(s) non résolu(s)")
        health.setdefault('details', {})['conflicts'] = remaining
        atomic_json(data/'health.json',health)
    history = load(data/'market_integrity_log.json', {'schema_version':1,'events':{}})
    if audit.get('corrections') or audit.get('refusals') or not audit.get('publication_safe'):
        # Provider observation time must not create a new event for every retry.
        identity = fingerprint({'session':audit.get('session'),'status':audit.get('status'),
            'totals':audit.get('totals'),'corrections':audit.get('corrections'),'refusals':audit.get('refusals')})
        event = history['events'].get(identity)
        if event:
            event['last_seen']=audit['observed_at'];event['occurrences']+=1
        else:
            history['events'][identity]={'first_seen':audit['observed_at'],'last_seen':audit['observed_at'],
                'occurrences':1,'audit':deepcopy(audit)}
    atomic_json(data/'market_integrity_log.json',history)
    memory = load(data/'error_memory.json', {})
    for lesson in [
        {'id':'volume_conflicts_need_corroboration','title':'Volumes de clôture corrigés tardivement',
         'rule':'Conserver avant/après et corriger uniquement les volumes confirmés ligne par ligne sur la même séance par deux fournisseurs. Ne pas effacer un conflit sans preuve.'},
        {'id':'money_is_not_share_quantity','title':'Colonne Qté monétaire dans un export PDF',
         'rule':'Lire les unités et le contrat de chaque champ. Le PDF Wafabourse du 18/10/2026 duplique les DH dans Qté ; utiliser QteEchangee de son API pour les titres.'},
        {'id':'totals_can_hide_offsetting_errors','title':'Un total égal peut masquer des erreurs opposées',
         'rule':'Contrôler aussi chaque ligne, les identités, les quantités, la séance et le périmètre ; une somme égale ne valide pas les composants.'}
    ]:
        if lesson['id'] not in memory.get('lessons', {}):
            memory=record_lesson(memory,lesson,now=audit['observed_at'])
    memory = update_error_memory(memory,audit,now=audit['observed_at'])
    atomic_json(data/'error_memory.json',memory)
    atomic_json(data/'market_integrity.json',audit)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cdg-input',type=Path)
    parser.add_argument('--secondary-input',type=Path,help='Already normalized dated observation; never a browser-supplied fact')
    args=parser.parse_args();data=ROOT/'data'
    fixture=load(data/'market_snapshot.json');overview=load(data/'market_overview.json',{}).get('current',{})
    now=datetime.now(CASABLANCA)
    if not args.cdg_input and (overview.get('status')=='intraday' or now.weekday()<5 and now.hour<16):
        audit={'schema_version':1,'session':overview.get('asof'),'observed_at':now.isoformat(),
            'status':'intraday','publication_safe':True,'internal_match':False,'cross_source_verified':False,
            'quantities_cross_source_verified':False,'providers':[],'totals':{},'corrections':[],'refusals':[],
            'notices':['Point provisoire : les contrôles de clôture définitive sont exécutés après 16h.']}
        persist_result(data,fixture,fixture,audit);print(json.dumps({'status':'intraday','publication_safe':True}));return 0
    with ThreadPoolExecutor(max_workers=2) as pool:
        primary=pool.submit(lambda:load(args.cdg_input) if args.cdg_input else fetch_cdg(timeout=20))
        secondary_future=pool.submit(lambda:load(args.secondary_input) if args.secondary_input else fetch_wafabourse(expected_session=overview.get('asof')))
        try:
            lines=primary.result();secondary=secondary_future.result()
            now=datetime.now(CASABLANCA)
            candidate,audit=reconcile_volumes(fixture,lines,overview,secondary,load(data/'source_codes.json'),now=now)
            for provider,payload in zip(audit['providers'],[lines,secondary]):
                provider['raw_sha256']=fingerprint(payload)
                provider['hash_kind']='canonical_observation_json_sha256'
        except Exception as exc:
            now=datetime.now(CASABLANCA)
            previous=load(data/'market_integrity.json',{})
            old_hash=hashlib.sha256((data/'market_snapshot.json').read_bytes()).hexdigest()
            reusable=bool(previous.get('publication_safe') and previous.get('validated_snapshot_sha256')==old_hash
                          and previous.get('session')==overview.get('asof'))
            candidate=fixture
            audit={'schema_version':1,'session':overview.get('asof'),'observed_at':now.isoformat(),
                'status':'unavailable','publication_safe':reusable,'internal_match':False,
                'cross_source_verified':False,'quantities_cross_source_verified':False,
                'providers':[{'provider':'CDG Capital Bourse','source_url':SOURCE_URL}],
                'totals':{},'corrections':[],'refusals':[{'reason':'Source de contrôle indisponible','code':'source_unavailable'}],
                'notices':['Dernier snapshot validé conservé ; aucun rapprochement actuel attesté.'],
                'failure_type':type(exc).__name__,'reused_last_validated_snapshot':reusable}
    persist_result(data,fixture,candidate,audit)
    print(json.dumps({k:audit.get(k) for k in ('status','session','publication_safe','cross_source_verified','quantities_cross_source_verified','totals')},ensure_ascii=False))
    return 0 if audit.get('publication_safe') else 1


if __name__=='__main__':
    sys.exit(main())
