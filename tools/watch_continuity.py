"""GitHub-hosted watchdog; no ChatGPT session, personal token or external message."""
from datetime import datetime
import json
import hashlib
import os
from pathlib import Path
import sys
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.continuity import assess,record_dispatch
from nour.market import atomic_json
from nour.runtime import ZONE
from nour.transactions import retry_transient

REPO='abdmoutalib207-lang/bvc-analyzer-nour'
PUBLIC='https://abdmoutalib207-lang.github.io/bvc-analyzer-nour/'


def github(path, body=None):
    token=os.environ['GH_TOKEN']
    req=Request('https://api.github.com/repos/'+REPO+'/'+path,
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                 'User-Agent':'Nour-continuity-watchdog'},
        data=json.dumps(body).encode() if body is not None else None,
        method='POST' if body is not None else 'GET')
    def request():
        with urlopen(req,timeout=20) as r:
            data=r.read();return json.loads(data) if data else {}
    return retry_transient(request,attempts=2)


def public_bytes(name):
    try:
        nonce=datetime.now(ZONE).strftime('%Y%m%d%H%M')
        with urlopen(Request(PUBLIC+name+'?nour_watch='+nonce,headers={'Cache-Control':'no-cache'}),timeout=15) as r:
            body=r.read(32*1024*1024+1)
            return body if len(body)<=32*1024*1024 else None
    except OSError:return None


def public(name):
    try:return json.loads(public_bytes(name) or b'{}')
    except ValueError:return {}


def main():
    now=datetime.now(ZONE)
    runs=github('actions/workflows/nour_daily.yml/runs?per_page=50')['workflow_runs']
    runtime=public('runtime.json');publication=public('publication.json')
    editions={slot:public('briefing-'+slug+'.json') for slot,slug in
              [('morning','matin'),('midday','midi'),('closing','cloture')]}
    path=ROOT/'data/continuity_state.json'
    previous=json.loads(path.read_text()) if path.exists() else None
    state,requests=assess(now,{'runtime':runtime,'publication':publication},editions,runs,previous)
    state.pop('publication_anomaly',None)
    state['public_manifest_observed']=bool(publication)
    state['artifact_hash_checks']={}
    observed_report={}
    for name in ('runtime.json','report.json','index.html','anomalies.json','couverture.json'):
        expected=(publication.get('sha256') or {}).get(name)
        if not expected:continue
        body=public_bytes(name)
        actual=hashlib.sha256(body).hexdigest() if body is not None else None
        state['artifact_hash_checks'][name]={'expected':expected,'actual':actual,'matched':actual==expected}
        if actual!=expected:state['publication_anomaly']='served_artifact_mismatch'
        if name=='report.json' and body:
            try:observed_report=json.loads(body)
            except ValueError:pass
    if not publication:state['publication_anomaly']='public_manifest_unavailable'
    if observed_report:
        state['source_observation']={k:(observed_report.get('health') or {}).get(k) for k in ('checked_at','result','last_session','message')}
        prices=[(r['symbol'],r.get('price')) for r in observed_report.get('results',[])]
        fingerprint=hashlib.sha256(json.dumps(prices,sort_keys=True).encode()).hexdigest()
        session=(observed_report.get('market_overview') or {}).get('asof')
        old=(previous or {}).get('market_fingerprint') or {}
        if old.get('prices_sha256')==fingerprint and old.get('session') and session and session>old['session']:
            state['source_warning']='all_prices_unchanged_across_new_market_session_requires_review'
        state['market_fingerprint']={'prices_sha256':fingerprint,'session':session}

    state['published_run_id']=publication.get('run_id')
    state['published_generator_commit']=publication.get('generator_commit')
    if runtime.get('run_id') and publication.get('run_id')!=runtime.get('run_id'):
        state['publication_anomaly']='runtime_manifest_mismatch'
    run=next((x for x in runs if str(x['id'])==str(publication.get('run_id'))),{})
    if run.get('conclusion') not in (None,'success'):
        state['publication_anomaly']='published_run_not_fully_verified'
    successful=next((x for x in runs if x.get('conclusion')=='success' and x.get('status')=='completed'),{})
    if successful.get('id') and publication.get('run_id') and int(successful['id'])>int(publication['run_id']):
        state['publication_anomaly']='newer_successful_run_not_visible'
    # GitHub concurrency keeps only one pending run: request one catch-up at a time.
    requests=requests[:1]
    for request in requests:
        accepted=False
        try:
            github('actions/workflows/nour_daily.yml/dispatches',
                {'ref':'main','inputs':{'slot':request['slot'],'scheduled_for':request['scheduled_for']}})
            accepted=True
        except (OSError,ValueError):pass
        record_dispatch(state,request,now,accepted)
    atomic_json(path,state)
    print(json.dumps({'checked_at':state['checked_at'],'expected':state['scheduled_events'],
        'catch_up_requests':len(requests),'publisher_active':state['publisher_active'],
        'publication_anomaly':state.get('publication_anomaly')},ensure_ascii=False))


if __name__=='__main__':main()
