"""Observed editions, missed schedules and bounded catch-up; Casablanca aware."""
from copy import deepcopy
from datetime import datetime, timedelta
from .runtime import ZONE

EDITION_CLOCKS={'morning':(9,45),'midday':(12,45),'closing':(16,0)}
INTERMEDIATE_CLOCKS=[(h,45) for h in (10,11,13,14,15,16,17)]+[(17,15)]


def expected_runs(now):
    now=now.astimezone(ZONE)
    if now.weekday()>=5:return []
    values=[dict(slot=s,target=now.replace(hour=h,minute=m,second=0,microsecond=0))
            for s,(h,m) in EDITION_CLOCKS.items()]
    values += [dict(slot='refresh',target=now.replace(hour=h,minute=m,second=0,microsecond=0))
               for h,m in INTERMEDIATE_CLOCKS]
    return sorted((x for x in values if x['target']+timedelta(minutes=20)<=now),key=lambda x:x['target'])


def assess(now, published, editions, runs, previous=None):
    now=now.astimezone(ZONE)
    state=deepcopy(previous or {'schema_version':1,'events':{}})
    dispatch=[];latest_refresh=None
    expected=expected_runs(now)
    for x in expected:
        if x['slot']=='refresh':latest_refresh=x['target']
    active=any(r.get('status') in ('queued','in_progress','requested','waiting','pending') for r in runs)
    runmap={str(r['id']):r for r in runs}
    for item in expected:
        target,slot=item['target'],item['slot'];key=target.isoformat()+'|'+slot
        event=state['events'].setdefault(key,dict(slot=slot,scheduled_for=target.isoformat(),
            first_detected=now.isoformat(),attempts=0,status='not_observed'))
        actual=(editions.get(slot) or {}).get('runtime',{}) if slot in EDITION_CLOCKS else published.get('runtime',{})
        stamp=actual.get('started_at');run=runmap.get(str(actual.get('run_id')))
        try:
            observed=datetime.fromisoformat(stamp).astimezone(ZONE)
            completed=bool(run and run.get('conclusion')=='success' and run.get('status')=='completed'
                and observed>=target and observed.date()==target.date()
                and (slot=='refresh' or actual.get('edition_for')==target.date().isoformat() and actual.get('slot')==slot))
        except (ValueError,TypeError):completed=False
        if completed:
            event.update(status='executed',observed_started_at=stamp,run_id=actual.get('run_id'),verified_at=now.isoformat())
            continue
        event.update(status='delayed_in_progress' if active else 'missed',last_detected=now.isoformat())
        if slot=='refresh' and target!=latest_refresh:
            event['status']='missed_superseded';continue
        last=event.get('last_attempt_at')
        cooled=not last or now-datetime.fromisoformat(last)>=timedelta(minutes=30)
        if not active and event['attempts']<3 and cooled:
            dispatch.append(dict(key=key,slot=slot,scheduled_for=target.isoformat()))
    state.update(checked_at=now.isoformat(),timezone='Africa/Casablanca',
        publisher_active=active,scheduled_events=len(expected),
        notice='Les heures planifiées ne sont jamais des preuves d’exécution. Rattrapages limités à trois tentatives, espacés de 30 minutes.')
    return state,dispatch


def record_dispatch(state, request, now, accepted):
    event=state['events'][request['key']]
    event['attempts']+=1;event['last_attempt_at']=now.isoformat()
    event['status']='catch_up_requested' if accepted else 'catch_up_request_failed'
    event.setdefault('attempt_history',[]).append(dict(at=now.isoformat(),accepted=accepted))


def publisher_failures(now, runs, published_run_id, previous=None):
    """A failed new deployment workflow is visible even if old Pages is healthy."""
    history=deepcopy(previous or {})
    for run in runs:
        if run.get('status')=='completed' and run.get('conclusion') in ('failure','timed_out','cancelled','action_required'):
            key=str(run['id'])
            event=history.setdefault(key,{'run_id':key,'first_detected':now.isoformat(),'state':'new'})
            event.update(last_detected=now.isoformat(),conclusion=run['conclusion'],url=run.get('html_url'))
    latest=runs[0] if runs else {}
    success=bool(latest.get('status')=='completed' and latest.get('conclusion')=='success'
                 and str(latest.get('id'))==str(published_run_id))
    if success:
        for event in history.values():
            if int(event['run_id'])<int(latest['id']) and event['state']!='resolved':
                event.update(state='resolved',resolved_at=now.isoformat(),resolution_run_id=str(latest['id']))
    latest_failed=bool(latest.get('status')=='completed' and latest.get('conclusion') in ('failure','timed_out','cancelled','action_required'))
    return history,latest_failed
