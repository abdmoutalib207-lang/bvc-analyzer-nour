"""Fault injection over the actual 80-title universe and atomic publication."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from nour.engine import build_report
from nour.analytics import technical
from nour.calculation_audit import audit_calculations
from nour.research import enrich
from nour.resilience import (GlobalIntegrityError, validate_fixture,
    isolate_audit_failures, health_with_quarantines)
from nour.transactions import site_transaction, retry_transient

ROOT=Path(__file__).resolve().parents[1]
ASOF='2026-10-23'


class ResilienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((ROOT/'data/market_snapshot.json').read_text())
        # Controlled numeric baseline for single-fault injection. Real source
        # quarantines are tested separately; never edit the production snapshot.
        for record in cls.fixture['records'].values():
            record.pop('quarantined_market',None)
        cls.facts=json.loads((ROOT/'data/facts_reference.json').read_text())['records']
        cls.baseline=build_report(cls.fixture,ASOF,facts=cls.facts)
        cls.original={r['symbol']:r for r in cls.baseline['results']}

    def check_others(self, report, affected):
        self.assertEqual(len(report['results']),80)
        for r in report['results']:
            if r['symbol'] not in affected:
                # Includes technical/fundamental numbers and canonical factors.
                self.assertEqual(r,self.original[r['symbol']],r['symbol'])

    def test_unknown_adi_technical_exception_preserves_all_other_79(self):
        def fault(record):
            if record.get('symbol')=='ADI':raise RuntimeError('injected')
            return technical(record)
        with patch('nour.engine.technical',side_effect=fault):
            report=build_report(self.fixture,ASOF,facts=self.facts)
        self.check_others(report,{'ADI'})
        adi=next(r for r in report['results'] if r['symbol']=='ADI')
        self.assertIsNone(adi['technical']['sma20'])
        self.assertIn('technical',adi['resilience']['suspended'])
        self.assertEqual(adi['fundamental'],self.original['ADI']['fundamental'])

    def test_several_titles_fail_independently(self):
        affected={'ADI','RDS','TGCC'}
        def fault(record):
            if record.get('symbol') in affected:raise ZeroDivisionError('injected')
            return technical(record)
        with patch('nour.engine.technical',side_effect=fault):
            report=build_report(self.fixture,ASOF,facts=self.facts)
        self.check_others(report,affected)

    def test_missing_price_is_not_a_valid_quote_and_others_unchanged(self):
        fixture=deepcopy(self.fixture);fixture['records']['ADI']['price']=None
        report=build_report(fixture,ASOF,facts=self.facts)
        self.check_others(report,{'ADI'})
        adi=next(r for r in report['results'] if r['symbol']=='ADI')
        self.assertIsNone(adi['price']);self.assertIsNone(adi['fundamental']['pe'])
        self.assertEqual(adi['decision'],'INDISPONIBLE')

    def test_financial_conflict_only_withholds_affected_per(self):
        facts=deepcopy(self.facts)
        facts['ADI'].setdefault('calculation_reservations',[]).append(dict(status='unresolved',
            metrics=['pe'],fields=['nombre_actions_au_rapport'],detail='Injected denominator conflict'))
        report=build_report(self.fixture,ASOF,facts=facts)
        self.check_others(report,{'ADI'})
        adi=next(r for r in report['results'] if r['symbol']=='ADI')
        self.assertIsNone(adi['fundamental']['pe'])
        self.assertEqual(adi['technical'],self.original['ADI']['technical'])
        self.assertEqual(adi['fundamental']['roe_pct'],self.original['ADI']['fundamental']['roe_pct'])

    def test_wrong_numeric_output_is_quarantined_not_counted_as_valid(self):
        report=deepcopy(self.baseline)
        report['masi_history']=json.loads((ROOT/'data/masi_history.json').read_text())['seances']
        enrich(report,self.fixture)
        next(r for r in report['results'] if r['symbol']=='ADI')['technical']['sma20']+=10
        audit=audit_calculations(self.fixture,report)
        self.assertTrue(any(f['symbol']=='ADI' and f['metric']=='technical.sma20' for f in audit['failures']))
        isolate_audit_failures(report,audit)
        checked=health_with_quarantines(audit_calculations(self.fixture,report),report)
        self.assertEqual(checked['status'],'degraded');self.assertFalse(checked['failures'])
        self.assertTrue(checked['quarantined_failures'])
        adi=next(r for r in report['results'] if r['symbol']=='ADI')
        self.assertIsNone(adi['technical']['sma20'])
        adi['technical']['sma20']=99999
        self.assertTrue(health_with_quarantines(audit_calculations(self.fixture,report),report)['failures'])

    def test_registry_corruption_is_global_not_locally_hidden(self):
        for mutate in (lambda f:f['symbols'].append('ADI'),
                       lambda f:f['records']['ADI'].update(symbol='RDS')):
            fixture=deepcopy(self.fixture);mutate(fixture)
            with self.assertRaises(GlobalIntegrityError):build_report(fixture,ASOF,facts=self.facts)

    def test_interrupted_publication_and_global_check_preserve_last_site(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'web';target.mkdir();(target/'index.html').write_text('healthy')
            for error in (RuntimeError,GlobalIntegrityError):
                with self.assertRaises(error):
                    with site_transaction(target) as stage:
                        (stage/'index.html').write_text('incomplete')
                        raise error('injected interruption')
                self.assertEqual((target/'index.html').read_text(),'healthy')
            with site_transaction(target) as stage:
                (stage/'index.html').write_text('new validated generation')
            self.assertEqual((target/'index.html').read_text(),'new validated generation')

    def test_suspended_title_and_session_without_transaction_are_local(self):
        fixture=deepcopy(self.fixture)
        fixture['records']['ADI'].update(suspended=True,price=None,price_asof=None)
        report=build_report(fixture,ASOF,facts=self.facts)
        self.check_others(report,{'ADI'})
        adi=next(r for r in report['results'] if r['symbol']=='ADI')
        self.assertEqual(adi['decision'],'SUSPENDU');self.assertIsNone(adi['fundamental']['pe'])
        fixture=deepcopy(self.fixture)
        # A zero-transaction row is not a new observed close and stays explicit.
        fixture['records']['ADI']['candles'][-1]['v']=0
        report=build_report(fixture,ASOF,facts=self.facts)
        self.check_others(report,{'ADI'})
        self.assertEqual(fixture['records']['ADI']['candles'][-1]['v'],0)
        self.assertGreaterEqual(next(r for r in report['results'] if r['symbol']=='ADI')['historical_statistics']['excluded_no_exchange_or_missing_sessions'],1)

    def test_full_atomic_build_publishes_all_80_with_adi_exception(self):
        import argparse,shutil
        import run
        baseline=json.loads((ROOT/'web/report.json').read_text())
        original={r['symbol']:r for r in baseline['results']}
        def fault(record):
            if record.get('symbol')=='ADI':raise RuntimeError('deliberate ADI fault')
            return technical(record)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            shutil.copytree(ROOT/'data',root/'data')
            target=root/'web';target.mkdir();(target/'index.html').write_text('previous healthy site')
            with patch.object(run,'ROOT',root),patch.dict('os.environ',{},clear=True),patch('nour.engine.technical',side_effect=fault):
                with site_transaction(target) as output:
                    run._build(argparse.Namespace(asof=ASOF,slot='refresh'),output)
            actual=json.loads((target/'report.json').read_text())
            self.assertEqual(len(list((target/'titres').glob('*.html'))),80)
            self.assertEqual(len(actual['results']),80)
            for row in actual['results']:
                if row['symbol']=='ADI':
                    self.assertIsNone(row['technical']['sma20'])
                    self.assertIn('Calcul technical interrompu',(target/'titres/ADI.html').read_text())
                else:
                    for key in ('technical','fundamental','canonical_score'):
                        self.assertEqual(row[key],original[row['symbol']][key],row['symbol']+' '+key)
            self.assertEqual(json.loads((target/'calculation-health.json').read_text())['status'],'degraded')
            self.assertNotIn('previous healthy site',(target/'index.html').read_text())

    def test_peer_comparison_exception_is_local_and_preserves_79(self):
        from nour.research import peers,peer_comparison,accounting_cohort
        baseline=deepcopy(self.baseline);peers(baseline['results'],self.fixture['records'])
        report=deepcopy(self.baseline)
        def broken(item,*args):
            if item['symbol']=='ADI':raise RuntimeError('peer injection')
            return peer_comparison(item,*args)
        with patch('nour.research.peer_comparison',side_effect=broken):peers(report['results'],self.fixture['records'])
        expected={r['symbol']:r for r in baseline['results']}
        for row in report['results']:
            if row['symbol']!='ADI':self.assertEqual(row,expected[row['symbol']])
            else:self.assertEqual(row['sector_comparison']['status'],'unavailable')
        self.assertIsNone(accounting_cohort({'accounting_basis':{'scope':'invalid'}}))

    def test_retry_is_limited_and_never_retries_validation_failure(self):
        attempts=[]
        def transient():
            attempts.append(1)
            if len(attempts)<3:raise URLError('temporary outage')
            return 'healthy'
        self.assertEqual(retry_transient(transient,wait=lambda _:None),'healthy')
        self.assertEqual(len(attempts),3)
        with self.assertRaises(URLError):retry_transient(lambda:(_ for _ in ()).throw(URLError('outage')),wait=lambda _:None)
        with self.assertRaises(ValueError):retry_transient(lambda:(_ for _ in ()).throw(ValueError('invalid')),wait=lambda _:None)


if __name__=='__main__':unittest.main()
