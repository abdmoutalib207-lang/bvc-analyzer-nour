"""Gate redundant wakes against the current local slot and verified public run."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.runtime import ZONE, current_target, opening_retry_due
from tools.watch_continuity import github, public_bytes


def decide(now, event, slot='auto', runtime=None, run=None, verified=False, requested_for=''):
    now=now.astimezone(ZONE)
    due=current_target(now)
    forced=event=='push' or event=='workflow_dispatch' and slot not in ('', 'auto') and not requested_for
    if forced:
        return dict(run=True,slot=slot or 'auto',scheduled_for='',reason='Explicit source rebuild or manual edition')
    if not due:
        return dict(run=False,slot='refresh',scheduled_for='',reason='Outside current weekday collection window')
    runtime=runtime or {};run=run or {}
    try:
        observed=datetime.fromisoformat(runtime['started_at']).astimezone(ZONE)
        done=bool(verified and str(run['id'])==str(runtime['run_id'])
                  and run.get('status')=='completed' and run.get('conclusion')=='success'
                  and due['target']<=observed<=now and observed.date()==now.date()
                  and runtime.get('slot')==due['slot']
                  and runtime.get('scheduled_at')==due['target'].isoformat()
                  and not opening_retry_due(now,runtime))
    except (KeyError,TypeError,ValueError):
        done=False
    return dict(run=not done,slot=due['slot'],scheduled_for=due['target'].isoformat(),
                reason='Current slot already published and verified' if done else 'Current local slot needs a verified publication')


def main():
    runtime={};run={};verified=False
    # A repository file, a generation timestamp or an accepted dispatch alone
    # never proves deployment. Refuse to skip when this evidence is unavailable.
    try:
        raw=public_bytes('runtime.json');manifest=json.loads(public_bytes('publication.json') or b'{}')
        runtime=json.loads(raw or b'{}')
        verified=bool(raw and manifest.get('sha256',{}).get('runtime.json')==hashlib.sha256(raw).hexdigest()
                      and str(manifest.get('run_id'))==str(runtime.get('run_id')) and runtime.get('run_id'))
        if verified:
            run=github('actions/runs/'+str(runtime['run_id']))
    except (OSError,ValueError,KeyError):
        verified=False
    result=decide(datetime.now(ZONE),os.environ.get('GITHUB_EVENT_NAME','workflow_dispatch'),
                  os.environ.get('NOUR_REQUESTED_SLOT','auto'),runtime,run,verified,os.environ.get('NOUR_REQUESTED_FOR',''))
    output=os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as stream:
            for key in ('run','slot','scheduled_for'):
                value=str(result[key]).lower() if isinstance(result[key],bool) else result[key]
                stream.write(f'{key}={value}\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
