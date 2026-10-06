import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from nour.research import prices, risk, lab, peers, net_return, archive_scores
from nour.engine import build_report, analyze
from nour.report_contracts import synchronize_market
from nour.research_view import page_body


def sample(n=460):
    days = [(date(2023,1,2)+timedelta(days=i)).isoformat() for i in range(n)]
    values = [100*(1.002**i)*(1+.004*(i%7)) for i in range(n)]
    bars = [{'d':d,'o':v,'h':v+1,'l':v-1,'c':v,'v':10000} for d,v in zip(days,values)]
    record = dict(symbol='AAA', name='Test', candles=bars, price=values[-1], price_asof=days[-1])
    fixture = dict(project='Nour', symbols=['AAA'], records={'AAA':record}, snapshot_updated=days[-1],
                   source_commit='test',source_files=[],market={})
    return fixture, dict(zip(days, values)), days[-1]


class ResearchTests(unittest.TestCase):
    def test_exact_date_pairing_beta_one_and_no_missing_drawdown(self):
        fixture, history, asof = sample()
        rec = fixture['records']['AAA']
        out = risk(rec,history,asof)
        self.assertEqual(out['beta'],1)
        self.assertEqual(out['correlation'],1)
        self.assertEqual(out['relative_return_pp'],0)
        rec['candles'].pop(-100)
        out = risk(rec,history,asof)
        self.assertEqual(out['paired_returns'],250)
        self.assertIsNone(out['drawdown_pct'])
        self.assertIsNone(out['relative_return_pp'])

    def test_invalid_duplicate_boolean_and_future_are_not_prices(self):
        fixture, history, asof = sample()
        rec=fixture['records']['AAA']
        broken=copy.deepcopy(rec['candles'][-2]);broken['c']=True
        rec['candles'][-2]=broken
        duplicate=copy.deepcopy(rec['candles'][-3]);rec['candles'].append(duplicate)
        future=copy.deepcopy(rec['candles'][-4]);future['d']='2099-01-01';rec['candles'].append(future)
        p=prices(rec,asof)
        self.assertNotIn(broken['d'],p)
        self.assertNotIn(duplicate['d'],p)
        self.assertNotIn('2099-01-01',p)

    def test_costs_compound_both_sides_not_subtraction(self):
        self.assertAlmostEqual(net_return(100,100,1,1),-1.9801980198)
        self.assertAlmostEqual(net_return(100,110,1,1,1),100*(110*.98/102-1))
        with self.assertRaises(ValueError): net_return(100,110,-1,1)

    def test_entry_after_signal_and_horizon_nonoverlap(self):
        fixture,history,asof=sample()
        out=lab(fixture,history,asof)
        rows=[r for r in out['rows'] if r['symbol']=='AAA' and r['horizon']==20]
        self.assertGreater(len(rows),0)
        days=list(history)
        for r in rows:
            self.assertEqual(days.index(r['entry_date']),days.index(r['signal_date'])+1)
            self.assertEqual(days.index(r['exit_date'])-days.index(r['entry_date']),20)
        for a,b in zip(rows,rows[1:]):self.assertLess(a['exit_date'],b['entry_date'])

    def test_missing_intervening_price_excludes_outcome_and_audit_balances(self):
        fixture,history,asof=sample()
        original=lab(fixture,history,asof)
        fixture['records']['AAA']['candles'].pop(220)
        out=lab(fixture,history,asof)
        self.assertLess(len([r for r in out['rows'] if r['symbol']=='AAA']),len([r for r in original['rows'] if r['symbol']=='AAA']))
        for a in out['audit']:
            self.assertEqual(a['candidates'],sum(a[k] for k in ('observed','missing','event_boundary','inactive','no_trend')))

    def test_future_mutation_does_not_change_past_study(self):
        fixture,history,asof=sample()
        cutoff=list(history)[350]
        before=lab(fixture,history,cutoff)
        for b in fixture['records']['AAA']['candles'][351:]:b['c']*=10
        for d in list(history)[351:]:history[d]*=100
        self.assertEqual(before,lab(fixture,history,cutoff))

    def test_event_and_suspension_guards(self):
        fixture,history,asof=sample()
        rec=fixture['records'].pop('AAA');rec['symbol']='CMT'
        fixture['records']['CMT']=rec;fixture['symbols']=['CMT']
        rec['suspended']=True
        out=lab(fixture,history,asof)
        self.assertFalse(any(r['symbol']=='CMT' for r in out['rows']))
        rec['suspended']=False;rec['resumed_recently']=True;rec['sessions_since_resume']=13
        self.assertEqual(risk(rec,history,asof)['status'],'insufficient')

    def test_peer_cohorts_are_strict_and_minimum_three_others(self):
        results=[];records={}
        for i in range(5):
            s=str(i);records[s]={'sector':'Banque'}
            results.append({'symbol':s,'decision':'OBSERVABLE','fundamental':{
                'accounting_basis':'Consolidé IFRS','exercise':2025,'currency':'MAD','pe':10+i,'pb':1+i,'roe_pct':5+i}})
        results[-1]['fundamental']['accounting_basis']='Social CGNC'
        peers(results,records)
        self.assertEqual(results[0]['sector_comparison']['metrics']['pe']['other_peers'],3)
        self.assertEqual(results[0]['sector_comparison']['metrics']['pe']['median'],12)
        self.assertEqual(results[-1]['sector_comparison']['metrics']['pe']['status'],'insufficient')
        results[1]['fundamental']['exercise']=2024
        peers(results,records)
        self.assertIsNone(results[0]['sector_comparison']['metrics']['pe']['median'])

    def test_peer_missing_denominator_never_inferred(self):
        results=[{'symbol':str(i),'decision':'OBSERVABLE','fundamental':{'accounting_basis':'Consolidé IFRS',
            'exercise':2025,'currency':'MAD','pe':None,'roe_pct':10}} for i in range(5)]
        peers(results,{str(i):{'sector':'Tech'} for i in range(5)})
        self.assertEqual(results[0]['sector_comparison']['metrics']['pe']['status'],'insufficient')
        self.assertIsNone(results[0]['sector_comparison']['metrics']['pe']['value'])

    def test_score_archive_first_observation_not_rewritten_or_backfilled(self):
        now=datetime(2026,10,6,1,tzinfo=timezone.utc)
        report={'analysis_date':'2026-10-06','source_commit':'abc','results':[
            {'symbol':'AAA','asof':'2026-10-05','canonical_score':{'value':50,'version':'v1'}}]}
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            first=archive_scores(report,folder,now)
            content=(folder/'2026-10-06.json').read_bytes()
            report['results'][0]['canonical_score']['value']=99
            archive_scores(report,folder,now)
            self.assertEqual(content,(folder/'2026-10-06.json').read_bytes())
            self.assertEqual(first['daily_snapshots'],1)
            report['analysis_date']='2026-10-05'
            archive_scores(report,folder,now)
            self.assertFalse((folder/'2026-10-05.json').exists())
            payload=json.loads(content)
            self.assertEqual(payload['first_observed_at'],now.isoformat())
            self.assertEqual(len(payload['observations'][0]['inputs_sha256']),64)

    def test_report_future_candles_cannot_change_past_technicals(self):
        fixture,history,asof=sample()
        cutoff=list(history)[350]
        before=build_report(fixture,cutoff)
        for b in fixture['records']['AAA']['candles'][351:]:b['c']*=10
        after=build_report(fixture,cutoff)
        self.assertEqual(before['results'][0]['technical'],after['results'][0]['technical'])
        self.assertEqual(before['results'][0]['historical_statistics'],after['results'][0]['historical_statistics'])
        self.assertIsNone(before['results'][0]['canonical_score']['value'])

    def test_nonfinite_engine_rows_and_future_overview_blocked(self):
        fixture,history,asof=sample()
        fixture['records']['AAA']['candles'][-2]['c']=float('nan')
        out=analyze(fixture['records']['AAA'],asof)
        self.assertEqual(out['decision'],'LIMITÉ')
        self.assertEqual(out['quality']['rejected_bars'],1)
        report={'analysis_date':asof}
        synchronize_market(report,{'asof':'2099-01-01','masi':{'value':999}})
        self.assertEqual(report['market']['status'],'unavailable')

    def test_payload_escapes_script_and_no_false_score_performance(self):
        fixture,history,asof=sample()
        report={'results':[],'research':lab(fixture,history,asof)}
        report['research']['limitations'].append('</script><script>alert(1)</script>')
        page=page_body(fixture,report)
        self.assertNotIn('</script><script>alert(1)',page)
        self.assertIn('aucune performance',page.lower())


if __name__=='__main__':unittest.main()
