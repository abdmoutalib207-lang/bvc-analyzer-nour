"""Regressions for stale cron events, verified-public gating and same-day catch-up."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from nour.runtime import ZONE, current_target, planned_runs, run_context, visible_intraday
from nour.continuity import assess
from tools.plan_market_run import decide

ROOT=Path(__file__).resolve().parents[1]

class HourlyClockTests(unittest.TestCase):
    def local(self,h,m=0,day=23):return datetime(2026,10,day,h,m,tzinfo=ZONE)

    def test_hourly_targets_and_19h_safety(self):
        targets=planned_runs(self.local(19,30))
        self.assertEqual([x['target'].strftime('%H:%M') for x in targets if x['target'].minute==45],
                         [f'{h:02d}:45' for h in range(9,18)])
        self.assertEqual(targets[-1]['target'].strftime('%H:%M'),'19:00')
        self.assertIsNone(current_target(self.local(9,44)))
        self.assertEqual(current_target(self.local(9,55))['target'].strftime('%H:%M'),'09:45')
        self.assertEqual(current_target(self.local(19))['target'].strftime('%H:%M'),'19:00')
        self.assertIsNone(current_target(self.local(20,15)))
        self.assertIsNone(current_target(self.local(12,day=24)))

    def test_old_cron_and_old_dispatch_do_not_make_yesterday_edition(self):
        ctx=run_context(self.local(14,5),'45 9 * * 1-5','schedule')
        self.assertEqual(ctx['slot'],'refresh');self.assertIn('13:45',ctx['scheduled_at'])
        self.assertEqual(ctx['edition_for'],'2026-10-23')
        self.assertIsNone(run_context(self.local(1),'0 16 * * 1-5','schedule')['scheduled_at'])
        result=decide(self.local(14,5),'workflow_dispatch','morning',requested_for='2026-10-22T09:45:00+00:00')
        self.assertTrue(result['run']);self.assertEqual(result['slot'],'refresh')
        self.assertEqual(result['scheduled_for'],self.local(13,45).isoformat())
        ctx=run_context(self.local(14,5),event='workflow_dispatch',slot='morning',
                        scheduled_for=self.local(9,45).isoformat())
        self.assertEqual(ctx['scheduled_at'],self.local(13,45).isoformat())
        with self.assertRaises(ValueError):
            run_context(self.local(14),event='workflow_dispatch',slot='morning',scheduled_for=self.local(9,45,day=22).isoformat())

    def test_generation_today_is_not_proof_of_current_session_or_slot(self):
        now=self.local(12,55)
        rt={'started_at':self.local(3).isoformat(),'built_at':now.isoformat(),'run_id':'1'}
        good={'id':1,'status':'completed','conclusion':'success'}
        self.assertTrue(decide(now,'schedule',runtime=rt,run=good,verified=True)['run'])
        rt.update(started_at=self.local(12,46).isoformat(),slot='midday',scheduled_at=self.local(12,45).isoformat())
        self.assertTrue(decide(now,'schedule',runtime=rt,run=good,verified=False)['run'])
        self.assertFalse(decide(now,'schedule',runtime=rt,run=good,verified=True)['run'])
        good['conclusion']='failure'
        self.assertTrue(decide(now,'schedule',runtime=rt,run=good,verified=True)['run'])

    def test_newest_slot_has_priority_over_missing_morning_and_midday(self):
        now=self.local(15,56)
        state,requests=assess(now,{},{},[])
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0]['scheduled_for'],self.local(15,45).isoformat())
        self.assertEqual(next(e for e in state['events'].values() if e['slot']=='morning')['status'],'missed_superseded')
        state,requests=assess(self.local(19,10),{},{},[],state)
        self.assertEqual(len(requests),1);self.assertEqual(requests[0]['scheduled_for'],self.local(19).isoformat())

    def test_later_publication_does_not_execute_all_missed_hours(self):
        now=self.local(14,10)
        rt=run_context(self.local(13,50),event='workflow_dispatch',slot='refresh',
                       scheduled_for=self.local(13,45).isoformat(),run_id='4')
        runs=[{'id':4,'status':'completed','conclusion':'success'}]
        state,requests=assess(now,{'runtime':rt},{},runs)
        executed=[e for e in state['events'].values() if e['status']=='executed']
        self.assertEqual(len(executed),1);self.assertEqual(executed[0]['scheduled_for'],self.local(13,45).isoformat())
        rt2=run_context(self.local(14,50),event='workflow_dispatch',slot='refresh',
                       scheduled_for=self.local(14,45).isoformat(),run_id='5')
        runs.insert(0,{'id':5,'status':'completed','conclusion':'success'})
        state,_=assess(self.local(15,10),{'runtime':rt2},{},runs,state)
        self.assertEqual(len([e for e in state['events'].values() if e['status']=='executed']),2)
        self.assertFalse(requests)

    def test_empty_opening_is_retried_once_after_0955(self):
        now=self.local(9,55)
        rt=run_context(self.local(9,46),event='workflow_dispatch',slot='morning',
                       scheduled_for=self.local(9,45).isoformat(),run_id='1')
        rt['collection']={'result':'awaiting_quotes'}
        good={'id':1,'status':'completed','conclusion':'success'}
        self.assertTrue(decide(now,'schedule',runtime=rt,run=good,verified=True)['run'])
        state,req=assess(now,{}, {'morning':{'runtime':rt}},[good])
        self.assertEqual(len(req),1)
        rt.update(started_at=now.isoformat(),run_id='2')
        good['id']=2
        self.assertFalse(decide(self.local(10,5),'schedule',runtime=rt,run=good,verified=True)['run'])
        self.assertFalse(assess(self.local(10,5),{}, {'morning':{'runtime':rt}},[good],state)[1])

    def test_legacy_false_executions_require_rechecking(self):
        target=self.local(9,45)
        previous={'schema_version':1,'events':{target.isoformat()+'|morning':
            {'slot':'morning','scheduled_for':target.isoformat(),'attempts':0,'status':'executed',
             'run_id':'1','observed_started_at':self.local(14).isoformat()}}}
        state,req=assess(self.local(14,10),{},{},[],previous)
        event=state['events'][target.isoformat()+'|morning']
        self.assertEqual(event['legacy_status'],'executed')
        self.assertEqual(event['status'],'missed_superseded')
        self.assertEqual(len(req),1)
        self.assertEqual(previous['events'][target.isoformat()+'|morning']['status'],'executed')

    def test_hourly_live_quote_retains_its_own_time_then_expires(self):
        point={'session':'2026-10-23','observed_at':self.local(9,45).isoformat(),'quotes':{'ADI':{'price':100}}}
        fresh=visible_intraday(point,self.local(10,44))
        self.assertEqual(fresh['status'],'provisional');self.assertEqual(fresh['age_minutes'],59)
        self.assertEqual(fresh['observed_at'],point['observed_at'])
        self.assertEqual(visible_intraday(point,self.local(11))['status'],'stale')
        self.assertFalse(visible_intraday(point,self.local(16))['quotes'])
        self.assertFalse(visible_intraday(point,self.local(10,day=26))['quotes'])

    def test_utc_conversions_follow_casablanca_at_both_offsets(self):
        for local in [datetime(2026,2,20,9,55,tzinfo=ZONE), self.local(9,55)]:
            utc=local.astimezone(timezone.utc)
            result=decide(utc,'schedule')
            self.assertEqual(datetime.fromisoformat(result['scheduled_for']).astimezone(timezone.utc),
                             local.replace(minute=45).astimezone(timezone.utc))

    def test_live_snapshot_advancing_cannot_poison_synthetic_volume_tests(self):
        from tests.test_local_market import universe,DAY,NOW
        from nour.volume_guard import reconcile_volumes
        original=json.loads((ROOT/'data/market_snapshot.json').read_text())
        original['market']['last_session']='2026-10-30'
        for record in original['records'].values():record['quarantined_market']={'session':'2026-10-30'}
        read=Path.read_text
        def altered(path,*a,**kw):
            return json.dumps(original) if path==ROOT/'data/market_snapshot.json' else read(path,*a,**kw)
        with patch.object(Path,'read_text',altered):inp=universe()
        _,proof=reconcile_volumes(*inp,now=NOW)
        self.assertTrue(proof['cross_source_verified'])
        self.assertEqual(inp[0]['market']['last_session'],DAY)

if __name__=='__main__':unittest.main()
