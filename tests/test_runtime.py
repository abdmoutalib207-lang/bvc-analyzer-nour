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
from nour.runtime import CONTROL_SLOTS, EDITIONS, EXTRA_WAKE_SCHEDULES, HOURLY_SLOTS, SLOTS, ZONE, run_context, visible_intraday
from nour.site import briefing_page, home_page
from nour.runtime import briefing_links

ROOT = Path(__file__).resolve().parents[1]


class RuntimeContracts(unittest.TestCase):
    def test_latest_closing_digest_replaces_stale_link_without_rewriting_edition(self):
        editions={'closing':{'title':'Édition de clôture',
                            'runtime':{'edition_for':'2026-10-20','run_id':'old'}}}
        before=copy.deepcopy(editions)
        links=briefing_links(editions,{'asof':'2026-10-23'})
        self.assertEqual(links,[{'label':'Dernière clôture disponible',
                                'date':'2026-10-23','url':'cloture.html'}])
        self.assertEqual(editions,before)
        self.assertEqual(briefing_links({}, {'asof':'2026-10-23'}),links)
        self.assertEqual(briefing_links(editions,{'asof':'bad'})[0]['date'],'2026-10-20')

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT/'data/market_snapshot.json').read_text())
        cls.codes = json.loads((ROOT/'data/source_codes.json').read_text())

    def row(self, ticker, day='05/10/2026', shares=1000):
        return {'Symbol': self.codes[ticker], 'DateDernierCours': day, 'Cours': 100,
                'Ouverture': 101, 'PlusHaut': 103, 'PlusBas': 98,
                'QteEchangee': shares, 'Volumes': shares*100}

    def test_hourly_local_collection_and_three_preserved_editions(self):
        workflow = (ROOT/'.github/workflows/nour_daily.yml').read_text()
        pairs = re.findall(r"cron: '([^']+)'\s+timezone: '([^']+)'", workflow)
        self.assertEqual(pairs, [(cron, 'Africa/Casablanca') for cron in (*SLOTS, *CONTROL_SLOTS, *HOURLY_SLOTS, *EXTRA_WAKE_SCHEDULES)])
        self.assertEqual(len(pairs), 13)
        clocks=[value[1] for value in (*SLOTS.values(), *CONTROL_SLOTS.values(), *HOURLY_SLOTS.values())]
        self.assertEqual(len(clocks),len(set(clocks)))
        self.assertEqual(sorted(clock for clock in clocks if clock.endswith(':45')),
                         [f'{hour:02d}:45' for hour in range(9,18)])
        for cron, (slot, clock, _) in HOURLY_SLOTS.items():
            hour,minute=map(int,clock.split(':'))
            ctx=run_context(datetime(2026,10,19,hour,minute,tzinfo=ZONE),cron,'schedule')
            self.assertEqual(ctx['slot'],'refresh')
            self.assertEqual(ctx['delay_minutes'],0)
            self.assertNotIn(ctx['slot'],EDITIONS)
        delayed=run_context(datetime(2026,10,19,12,30,tzinfo=ZONE),'45 10 * * 1-5','schedule')
        self.assertEqual(delayed['target_time'],'11:45')
        self.assertEqual(delayed['delay_minutes'],45)
        self.assertTrue(delayed['late'])
        overnight=run_context(datetime(2026,10,19,1,0,tzinfo=ZONE),'45 17 * * 1-5','schedule')
        self.assertEqual(overnight['edition_for'],'2026-10-19')
        control=run_context(datetime(2026,10,19,17,15,tzinfo=ZONE),'15 17 * * 1-5','schedule')
        self.assertEqual(control['slot'],'refresh')
        self.assertNotIn(control['slot'],EDITIONS)
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

    def test_late_run_updates_current_slot_and_actual_time(self):
        ctx = run_context(datetime(2026,10,5,14,0,tzinfo=ZONE), '45 9 * * 1-5','schedule')
        self.assertEqual(ctx['slot'],'refresh')
        self.assertEqual(ctx['delay_minutes'],15)
        self.assertFalse(ctx['late'])
        self.assertIn('13:45',ctx['scheduled_at'])
        overnight = run_context(datetime(2026,10,6,1,0,tzinfo=ZONE), '0 16 * * 1-5','schedule')
        self.assertEqual(overnight['edition_for'],'2026-10-06')
        self.assertIsNone(overnight['delay_minutes'])
        self.assertIsNone(overnight['scheduled_at'])
        with self.assertRaises(ValueError):
            run_context(schedule='unexpected',event='schedule')
        self.assertEqual(run_context(event='push')['slot'],'adhoc')
        self.assertEqual(run_context(event='workflow_dispatch',slot='refresh')['slot'],'refresh')
        self.assertEqual(run_context(event='workflow_dispatch',slot='preclose')['slot'],'preclose')

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
            point=capture_intraday(self.fixture,lines+[self.row('STK')],self.codes,datetime(2026,10,5,9,45,tzinfo=ZONE))
            self.assertNotIn('ADI',point['quotes'])
            self.assertIn('STK',point['quotes'])
            self.assertTrue(point['rejected'])
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
        # The production snapshot advances on every market update. This test
        # must explicitly simulate an absent closing, not depend on its age.
        for item in report['results']:
            item['asof'] = '2026-10-02'
        report['runtime'] = run_context(datetime(2026,10,5,16,25,tzinfo=ZONE), '0 16 * * 1-5','schedule')
        brief = create_briefing(report)
        self.assertEqual(brief['edition_status'],'closing_pending')
        page = briefing_page(self.fixture,brief,'','')
        self.assertIn('Clôture du jour non confirmée',page)
        self.assertIn('Créneau exécuté en retard',page)
        self.assertIn('09:45 · 12:45 · 16:00',page)
        self.assertIn('Dernière clôture',home_page(self.fixture,report,'',''))
        report['results'][0]['asof'] = '2026-10-05'
        self.assertEqual(create_briefing(report)['edition_status'], 'published')

    def test_archive_preserves_editions_across_intermediate_and_push_builds(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target/'data').mkdir(); (target/'web').mkdir()
            for filename in ('market_snapshot.json','news.json','facts_reference.json','issuer_status.json','source_codes.json'):
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
