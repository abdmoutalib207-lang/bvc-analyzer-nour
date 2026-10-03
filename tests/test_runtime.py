"""Scheduling, live/close separation, and independent briefing publication."""
import copy
import io
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import run
from nour.briefing import create_briefing
from nour.engine import build_report
from nour.market import capture_intraday, import_session
from nour.runtime import EDITIONS, SLOTS, ZONE, run_context, visible_intraday
from nour.site import briefing_page, home_page

ROOT = Path(__file__).resolve().parents[1]


class RuntimeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT/'data/market_snapshot.json').read_text())
        cls.codes = json.loads((ROOT/'data/source_codes.json').read_text())

    def row(self, ticker, day='05/10/2026', shares=1000):
        return {'Symbol': self.codes[ticker], 'DateDernierCours': day, 'Cours': 100,
                'Ouverture': 101, 'PlusHaut': 103, 'PlusBas': 98,
                'QteEchangee': shares, 'Volumes': shares*100}

    def test_five_exact_local_slots_and_three_editions(self):
        workflow = (ROOT/'.github/workflows/nour_daily.yml').read_text()
        pairs = re.findall(r"cron: '([^']+)'\s+timezone: '([^']+)'", workflow)
        self.assertEqual(pairs, [(cron, 'Africa/Casablanca') for cron in SLOTS])
        self.assertEqual(set(EDITIONS), {'morning','midday','closing'})
        for cron, (slot, clock, _) in SLOTS.items():
            h,m = map(int,clock.split(':'))
            ctx = run_context(datetime(2026,10,5,h,m,tzinfo=ZONE), cron, 'schedule')
            self.assertEqual(ctx['slot'], slot)
            self.assertEqual(ctx['delay_minutes'], 0)
        # Follow the installed IANA database, not a presumed UTC offset. Morocco
        # can change its clock policy; runners need not share a tzdata release.
        for month, day in [(2,20),(10,5)]:
            local = datetime(2026,month,day,9,45,tzinfo=ZONE)
            ctx = run_context(local, '45 9 * * 1-5','schedule')
            self.assertEqual(datetime.fromisoformat(ctx['scheduled_at']).hour,9)
            expected = local.astimezone(timezone.utc)
            self.assertEqual(datetime.fromisoformat(ctx['scheduled_at']).astimezone(timezone.utc),expected)

    def test_late_run_keeps_original_slot_and_actual_time(self):
        ctx = run_context(datetime(2026,10,5,14,0,tzinfo=ZONE), '45 9 * * 1-5','schedule')
        self.assertEqual(ctx['slot'],'morning')
        self.assertEqual(ctx['delay_minutes'],255)
        self.assertTrue(ctx['late'])
        self.assertIn('09:45',ctx['scheduled_at'])
        overnight = run_context(datetime(2026,10,6,1,0,tzinfo=ZONE), '0 18 * * 1-5','schedule')
        self.assertEqual(overnight['edition_for'],'2026-10-05')
        self.assertEqual(overnight['delay_minutes'],420)
        with self.assertRaises(ValueError):
            run_context(schedule='unexpected',event='schedule')
        self.assertEqual(run_context(event='push')['slot'],'adhoc')

    def test_intraday_true_extremes_identity_and_no_history_mutation(self):
        original = copy.deepcopy(self.fixture)
        point = capture_intraday(self.fixture,[self.row('STK'), self.row('SNA'),
                    self.row('ADI',shares=0),self.row('SMI',day='02/10/2026')],self.codes,
                    now=datetime(2026,10,5,11,46,tzinfo=ZONE))
        self.assertEqual(set(point['quotes']),{'STK','SNA'})
        self.assertEqual(point['quotes']['STK']['high'],103)
        self.assertEqual(point['quotes']['SNA']['low'],98)
        self.assertTrue(point['quotes']['STK']['provisional'])
        self.assertEqual(self.fixture,original)
        # Current-session prices remain unfit for closing candles before 16h.
        with self.assertRaises(ValueError):
            import_session(self.fixture,[self.row('STK')],self.codes,
                now=datetime(2026,10,5,11,46,tzinfo=ZONE),minimum=1)

    def test_live_rejects_bad_rows_future_collisions_and_cancelled_session(self):
        bad = self.row('ADI'); bad['PlusHaut'] = None
        point = capture_intraday(self.fixture,[bad,self.row('STK')],self.codes,
                    now=datetime(2026,10,5,9,45,tzinfo=ZONE))
        self.assertNotIn('ADI',point['quotes'])
        self.assertEqual(len(point['rejected']),1)
        for lines in [[self.row('ADI',day='06/10/2026')],[self.row('ADI'),self.row('ADI')]]:
            with self.assertRaises(ValueError):
                capture_intraday(self.fixture,lines,self.codes,datetime(2026,10,5,9,45,tzinfo=ZONE))
        with self.assertRaises(ValueError):
            capture_intraday(self.fixture,[],self.codes,datetime(2026,9,17,9,45,tzinfo=ZONE))

    def test_cache_is_never_relabelled_fresh(self):
        point = capture_intraday(self.fixture,[self.row('ADI')],self.codes,
                    now=datetime(2026,10,5,9,45,tzinfo=ZONE))
        self.assertEqual(visible_intraday(point,datetime(2026,10,5,9,50,tzinfo=ZONE))['status'],'provisional')
        for time in [datetime(2026,10,5,11,0,tzinfo=ZONE),datetime(2026,10,6,9,45,tzinfo=ZONE),
                     datetime(2026,10,5,18,0,tzinfo=ZONE)]:
            old = visible_intraday(point,time)
            self.assertEqual(old['status'],'stale')
            self.assertEqual(old['quotes'],{})
            self.assertEqual(old['observed_at'],point['observed_at'])

    def test_missing_closing_and_delays_are_visible_not_success_claims(self):
        report = build_report(self.fixture,'2026-10-05')
        report['runtime'] = run_context(datetime(2026,10,5,19,0,tzinfo=ZONE), '0 18 * * 1-5','schedule')
        brief = create_briefing(report)
        self.assertEqual(brief['edition_status'],'closing_pending')
        page = briefing_page(self.fixture,brief,'','')
        self.assertIn('Clôture du jour non confirmée',page)
        self.assertIn('Créneau exécuté en retard',page)
        self.assertIn('09:45 · 11:46 · 13:45 · 15:45 · 18:00',page)
        self.assertIn('Dernière clôture',home_page(self.fixture,report,'',''))

    def test_archive_preserves_editions_across_intermediate_and_push_builds(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target/'data').mkdir(); (target/'web').mkdir()
            for filename in ('market_snapshot.json','news.json','facts_reference.json'):
                shutil.copyfile(ROOT/'data'/filename,target/'data'/filename)
            with patch.object(run,'ROOT',target), patch.dict('os.environ',{},clear=True), redirect_stdout(io.StringIO()):
                for slot in ('morning','midday','closing'):
                    with patch('sys.argv',['run.py','--asof','2026-10-03','--slot',slot]):
                        run.main()
                archives = {p.name:p.read_bytes() for p in (target/'data/briefings').glob('*.json')}
                self.assertEqual(len(archives),3)
                for slot in ('refresh','preclose','auto'):
                    with patch('sys.argv',['run.py','--asof','2026-10-03','--slot',slot]):
                        run.main()
                self.assertEqual(archives,{p.name:p.read_bytes() for p in (target/'data/briefings').glob('*.json')})
                for slug in EDITIONS.values():
                    self.assertTrue((target/f'web/briefing-{slug}.html').is_file())
                manifest=json.loads((target/'web/runtime.json').read_text())
                self.assertEqual(len(manifest['briefings']),3)
                self.assertEqual(manifest['publication_stage'],'built_before_pages_deployment')


if __name__ == '__main__':
    unittest.main()
