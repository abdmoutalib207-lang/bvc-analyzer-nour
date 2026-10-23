import unittest
from datetime import datetime,timezone,timedelta
from nour.runtime import ZONE,run_context
from nour.continuity import assess,record_dispatch,expected_runs,publisher_failures

class ContinuityTests(unittest.TestCase):
    def test_missed_is_not_executed_and_retries_are_bounded(self):
        # The 19h safety slot remains current long enough for three bounded retries.
        now=datetime(2026,10,23,19,10,tzinfo=ZONE)
        state,requests=assess(now,{}, {}, [])
        self.assertEqual(len(requests),1)
        req=requests[0]
        self.assertEqual(state['events'][req['key']]['status'],'missed')
        record_dispatch(state,req,now,True)
        self.assertEqual(state['events'][req['key']]['status'],'catch_up_requested')
        self.assertFalse(assess(now+timedelta(minutes=1),{},{},[],state)[1])
        for n in range(2):
            now+=timedelta(minutes=30)
            state,requests=assess(now,{},{},[],state)
            self.assertEqual(len(requests),1)
            self.assertEqual(requests[0]['key'],req['key'])
            record_dispatch(state,req,now,True)
        self.assertFalse(assess(now+timedelta(minutes=1),{},{},[],state)[1])

    def test_only_actual_successful_published_edition_counts(self):
        now=datetime(2026,10,23,10,10,tzinfo=ZONE)
        rt=run_context(now,event='workflow_dispatch',slot='morning',scheduled_for=now.replace(hour=9,minute=45).isoformat(),run_id='9')
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
        # Installed IANA releases can differ after a Moroccan clock-policy change.
        # Test the local-clock/UTC conversion, never impose a historical offset.
        for local in (feb,octo):
            context=run_context(local,'45 9 * * 1-5','schedule')
            observed=datetime.fromisoformat(context['scheduled_at'])
            self.assertEqual(observed.hour,9);self.assertEqual(observed.minute,45)
            self.assertEqual(observed.astimezone(timezone.utc),local.astimezone(timezone.utc))
            self.assertEqual(observed.utcoffset(),local.utcoffset())
        self.assertFalse(expected_runs(datetime(2026,10,24,20,tzinfo=ZONE)))
        for target in ('2026-10-23T11:45:00+01:00','2026-10-24T09:45:00+01:00','2026-10-23T09:45:00'):
            with self.assertRaises(ValueError):run_context(octo,event='workflow_dispatch',slot='morning',scheduled_for=target)

    def test_refreshes_are_observed_but_only_latest_is_caught_up(self):
        state,req=assess(datetime(2026,10,23,18,10,tzinfo=ZONE),{},{},[])
        self.assertEqual(sum(r['slot']=='refresh' for r in req),1)
        self.assertEqual(sum(e['status']=='missed_superseded' for e in state['events'].values()),10)
        self.assertEqual(req[0]['scheduled_for'],datetime(2026,10,23,17,45,tzinfo=ZONE).isoformat())

    def test_failed_new_publication_is_detected_despite_healthy_old_pages(self):
        now=datetime(2026,10,23,10,10,tzinfo=ZONE)
        failed={'id':20,'status':'completed','conclusion':'failure'}
        old={'id':19,'status':'completed','conclusion':'success'}
        history,bad=publisher_failures(now,[failed,old],'19')
        self.assertTrue(bad);self.assertEqual(history['20']['state'],'new')
        healthy={'id':21,'status':'completed','conclusion':'success'}
        retained,_=publisher_failures(now,[healthy,failed],'19',history)
        self.assertNotEqual(retained['20']['state'],'resolved')
        resolved,bad=publisher_failures(now,[healthy,failed],'21',history)
        self.assertFalse(bad);self.assertEqual(resolved['20']['state'],'resolved')
        self.assertEqual(resolved['20']['first_detected'],history['20']['first_detected'])
