from contextlib import redirect_stdout
from datetime import datetime,timedelta
import io
from pathlib import Path
import unittest
from nour.runtime import ZONE
from tools.relay_market_clock import next_wake,relay

class ClockRelayTests(unittest.TestCase):
    def local(self,h,m=0,day=23):return datetime(2026,10,day,h,m,tzinfo=ZONE)

    def test_next_hour_opening_retry_controls_and_19h(self):
        for h,m,target in [(9,30,'09:45'),(9,50,'09:55'),(9,56,'10:45'),
                           (15,55,'16:00'),(17,20,'17:45'),(17,46,'19:00'),(18,59,'19:00')]:
            self.assertEqual(next_wake(self.local(h,m)).strftime('%H:%M'),target)
        self.assertIsNone(next_wake(self.local(19)))
        self.assertIsNone(next_wake(self.local(3)))
        self.assertIsNone(next_wake(self.local(10,day=24)))

    def test_relay_waits_then_dispatches_exact_nour_workflow_once(self):
        tick=[self.local(10,40)];sleeps=[];calls=[]
        def sleep(seconds):
            self.assertLessEqual(seconds,30);sleeps.append(seconds);tick[0]+=timedelta(seconds=seconds)
        with redirect_stdout(io.StringIO()) as out:
            self.assertTrue(relay(lambda:tick[0],sleep,lambda *args:calls.append(args)))
        self.assertEqual(sum(sleeps),300)
        self.assertEqual(calls,[('actions/workflows/nour_daily.yml/dispatches',{'ref':'main','inputs':{'slot':'auto'}})])
        self.assertIn('dispatch_accepted',out.getvalue());self.assertIn('not publication proof',out.getvalue())

    def test_weekend_or_after_safety_never_dispatches_or_sleeps(self):
        def unexpected(*a):self.fail('Outside-window relay did work')
        for now in (self.local(19,1),self.local(10,day=24)):
            with redirect_stdout(io.StringIO()):self.assertFalse(relay(lambda:now,unexpected,unexpected))

    def test_delayed_or_cross_day_wake_is_refused(self):
        for late in (self.local(11,5),self.local(10,45,day=26)):
            tick=[self.local(10,44)]
            def jump(seconds):tick[0]=late
            with redirect_stdout(io.StringIO()),self.assertRaises(ValueError):
                relay(lambda:tick[0],jump,lambda *a:self.fail('Stale relay dispatched'))

    def test_wait_uses_separate_lock_and_nour_scope_guard(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/nour_relay.yml').read_text()
        self.assertIn('group: nour-hourly-relay',workflow)
        self.assertNotIn('group: nour-publication',workflow)
        self.assertIn('python tools/assert_nour_scope.py',workflow)
        self.assertIn('timeout-minutes: 85',workflow)
        self.assertNotIn('-bvc-analyzer',workflow)
