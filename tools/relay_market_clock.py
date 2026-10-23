"""Bounded GitHub-hosted relay; no cron wait after the first daily wake."""
from datetime import datetime
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.runtime import ZONE, planned_runs
from tools.watch_continuity import github


def next_wake(now):
    now=now.astimezone(ZONE)
    targets=[item['target'] for item in planned_runs(now)]
    if targets:targets.append(now.replace(hour=9,minute=55,second=0,microsecond=0))
    target=min((target for target in targets if target>now),default=None)
    return target if target and (target-now).total_seconds()<=75*60 else None


def relay(now=None, sleep=time.sleep, dispatch=github):
    clock=now or (lambda:datetime.now(ZONE))
    target=next_wake(clock())
    if target is None:
        print(json.dumps({'status':'outside_window','observed_at':clock().isoformat()}));return False
    seconds=(target-clock()).total_seconds()
    if seconds<0 or seconds>75*60:
        raise ValueError('Relay target outside the bounded current-day window')
    print(json.dumps({'status':'waiting','target':target.isoformat(),'observed_at':clock().isoformat(),
                      'notice':'Waiting is not an execution or publication proof'}),flush=True)
    while True:
        remaining=(target-clock()).total_seconds()
        if remaining<=0:break
        sleep(min(remaining,30))
    actual=clock()
    if actual.date()!=target.date() or (actual-target).total_seconds()>15*60:
        raise ValueError('Relay woke too late; let the watchdog choose the current slot')
    dispatch('actions/workflows/nour_daily.yml/dispatches',{'ref':'main','inputs':{'slot':'auto'}})
    print(json.dumps({'status':'dispatch_accepted','target':target.isoformat(),
                      'requested_at':actual.isoformat(),'notice':'Dispatch acceptance is not publication proof'}),flush=True)
    return True


if __name__=='__main__':relay()
