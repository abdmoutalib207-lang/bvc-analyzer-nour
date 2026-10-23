import unittest
from datetime import datetime,timezone,timedelta
from nour.runtime import ZONE,run_context
from nour.continuity import assess,record_dispatch,expected_runs

class ContinuityTests(unittest.TestCase):
    def test_missed_is_not_executed_and_retries_are_bounded(self):
        now=datetime(2026,10,23,10,10,tzinfo=ZONE)
        state,requests=assess(now,{}, {}, [])
        self.assertEqual(len(requests),1)
        req=requests[0]
        self.assertEqual(state['events'][req['key']]['status'],'missed')
        record_dispatch(state,req,now,True)
        self.assertEqual(state['events'][req['key']]['status'],'catch_up_requested')
        self.assertFalse(assess(now+timedelta(minutes=1),{},{},[],state)[1])
        for n in range(2):
            now+=timedelta(minutes=31)
            state,requests=assess(now,{},{},[],state)
            req=next(r for r in requests if r['slot']=='morning')
            record_dispatch(state,req,now,True)
        now+=timedelta(minutes=31)
        state,requests=assess(now,{},{},[],state)
        self.assertFalse(any(r['slot']=='morning' for r in requests))

    def test_only_actual_successful_published_edition_counts(self):
        now=datetime(2026,10,23,10,10,tzinfo=ZONE)
        rt=run_context(now,event='workflow_dispatch',slot='morning',scheduled_for='2026-10-23T09:45:00+01:00',run_id='9')
        self.assertTrue(rt['late']);self.assertEqual(rt['delay_minutes'],25)
        self.assertEqual(rt['scheduled_at_basis'],'watchdog_requested_occurrence')
        runs=[dict(id=9,status='completed',conclusion='success')]
        state,req=assess(now,{}, {'morning':{'runtime':rt}},runs)
        self.assertFalse(req);self.assertEqual(next(iter(state['events'].values()))['status'],'executed')
        runs[0]['conclusion']='failure'
        self.assertTrue(assess(now,{}, {'morning':{'runtime':rt}},runs)[1])
        self.assertFalse(assess(now,{}, {},[dict(id=10,status='queued')])[1])

    def test_casablanca_ramadan_offset_and_weekend(self):
        feb=datetime(2026,2,20,9,45,tzinfo=ZONE)
        octo=datetime(2026,10,23,9,45,tzinfo=ZONE)
        self.assertEqual(feb.utcoffset(),timedelta(0))
        self.assertEqual(octo.utcoffset(),timedelta(hours=1))
        self.assertFalse(expected_runs(datetime(2026,10,24,20,tzinfo=ZONE)))
        for target in ('2026-10-23T11:45:00+01:00','2026-10-24T09:45:00+01:00','2026-10-23T09:45:00'):
            with self.assertRaises(ValueError):run_context(octo,event='workflow_dispatch',slot='morning',scheduled_for=target)

    def test_refreshes_are_observed_but_only_latest_is_caught_up(self):
        state,req=assess(datetime(2026,10,23,18,10,tzinfo=ZONE),{},{},[])
        self.assertEqual(sum(r['slot']=='refresh' for r in req),1)
        self.assertEqual(sum(e['status']=='missed_superseded' for e in state['events'].values()),7)
