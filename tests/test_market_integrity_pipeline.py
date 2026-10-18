from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from nour.market import atomic_json
from nour.market_integrity import visible_integrity
from tools.check_market_integrity import persist_result
from tools.audit_market_integrity import audit_market_integrity


class MarketIntegrityPipeline(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.data=Path(self.temp.name)
        self.fixture={'records':{'ABC':{'candles':[dict(d='2026-10-16',o=10,h=10,l=10,c=10,v=1,turnover_mad=10)],'day_shares':1,'day_turnover_mad':10}}}
        self.candidate=deepcopy(self.fixture);r=self.candidate['records']['ABC'];r['candles'][0].update(v=2,turnover_mad=20);r.update(day_shares=2,day_turnover_mad=20)
        atomic_json(self.data/'market_snapshot.json',self.fixture)
        self.audit=dict(status='reconciled',session='2026-10-16',observed_at='2026-10-18T20:00:00+00:00',publication_safe=True,
            internal_match=True,cross_source_verified=True,quantities_cross_source_verified=True,
            validated_symbols=['ABC'],validated_fields=['v','day_shares','day_turnover_mad','turnover_mad'],
            providers=[{'provider':'CDG','source_url':'https://www.cdgcapitalbourse.ma/api/','raw_sha256':'a'*64},
                       {'provider':'Wafa','source_url':'https://www.wafabourse.com/fr/market-tracking/instruments-financiers','raw_sha256':'b'*64}],
            totals={'retained_after':{'turnover_mad':'20','shares':2,'quoted':1},'secondary':{'turnover_mad':'20','shares':2,'quoted':1}},
            corrections=[{'symbol':'ABC','session':'2026-10-16','fields':['v'], 'before':{'v':1},'after':{'v':2}}],refusals=[])

    def report(self):
        return {'market_overview':{'asof':'2026-10-16','status':'closed','turnover_mad':20,'shares':2,'breadth':{'quoted':1}},
            'results':[{'symbol':'ABC','asof':'2026-10-16','day_shares':2,'day_turnover_mad_actual':20}],
            'provenance':{'market_snapshot_sha256':self.audit.get('validated_snapshot_sha256')},
            'cross_source_volume_audit':self.audit}

    def test_correction_and_memory_persist_but_malformed_conflict_is_not_resolved(self):
        conflicts=[{'symbol':'ABC','session':'2026-10-16','fields':['v'],'observed':{'v':2}},
                   {'symbol':'UNKNOWN','session':'2026-10-16','fields':[],'observed':{}}]
        atomic_json(self.data/'health.json',{'details':{'conflicts':conflicts}})
        persist_result(self.data,self.fixture,self.candidate,self.audit)
        health=json.loads((self.data/'health.json').read_text())
        self.assertEqual(len(health['details']['conflicts']),1)
        self.assertEqual(health['details']['conflicts'][0]['symbol'],'UNKNOWN')
        self.assertEqual(json.loads((self.data/'market_snapshot.json').read_text()),self.candidate)
        memory=json.loads((self.data/'error_memory.json').read_text())
        self.assertEqual(len(memory['entries']),1)
        self.assertEqual(next(iter(memory['entries'].values()))['status'],'resolved')
        self.assertEqual(len(memory['lessons']),3)
        self.assertEqual(len(json.loads((self.data/'market_integrity_log.json').read_text())['events']),1)
        self.assertFalse(audit_market_integrity(self.report())['failures'])

    def test_refusal_never_overwrites_market_but_is_remembered(self):
        before=(self.data/'market_snapshot.json').read_bytes()
        self.audit.update(status='conflict',publication_safe=False,cross_source_verified=False,corrections=[],
                          refusals=[{'code':'source_conflict','symbol':'ABC','fields':['v']}])
        persist_result(self.data,self.fixture,self.candidate,self.audit)
        self.assertEqual((self.data/'market_snapshot.json').read_bytes(),before)
        self.assertTrue((self.data/'error_memory.json').exists())
        self.assertTrue(audit_market_integrity(self.report())['failures'])

    def test_matched_label_requires_exact_snapshot_and_both_sources(self):
        self.audit['validated_snapshot_sha256']='c'*64
        report=self.report()
        for field,value in [('cross_source_verified',False),('internal_match',False),('validated_snapshot_sha256','d'*64)]:
            bad=deepcopy(self.audit);bad[field]=value
            self.assertEqual(visible_integrity(bad,report)['status'],'stale')
            report['cross_source_volume_audit']=bad
            self.assertTrue(audit_market_integrity(report)['failures'])

    def test_quantities_or_aggregates_cannot_be_lost_in_export(self):
        self.audit['validated_snapshot_sha256']='c'*64
        report=self.report();report['results'][0]['day_shares']=3
        self.assertTrue(audit_market_integrity(report)['failures'])
        report=self.report();report['cross_source_volume_audit']['totals']['secondary']['shares']=3
        self.assertTrue(audit_market_integrity(report)['failures'])
