from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import unittest
from nour.engine import build_report
from nour.local_market import isolate_market_lines,validated_local_scope
from nour.market import import_session
from nour.volume_guard import reconcile_volumes
from tools.audit_market_integrity import audit_market_integrity
ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-22';NOW=datetime(2026,10,23,19,tzinfo=timezone.utc)

def universe():
    fixture=json.loads((ROOT/'data/market_snapshot.json').read_text());codes=json.loads((ROOT/'data/source_codes.json').read_text())
    raw=[];secondary=[]
    for i,s in enumerate(fixture['symbols']):
        price=i+100;bar=dict(d=DAY,o=price,h=price+1,l=price-1,c=price,v=100,turnover_mad=price*100)
        rec=fixture['records'][s];rec.update(price=price,price_asof=DAY,day_shares=100,day_turnover_mad=price*100,stale=False,suspended=False)
        rec['candles']=[b for b in rec['candles'] if b['d']<DAY]+[bar]
        raw.append(dict(Symbol=codes[s],DateDernierCours='22/10/2026 15:30:00',Cours=price,Ouverture=price,PlusHaut=price+1,PlusBas=price-1,QteEchangee=100,Volumes=price*100))
        secondary.append(dict(symbol=codes[s],session=DAY,price=price,shares=100,amount_mad=price*100))
    overview=dict(asof=DAY,status='closed',turnover_mad=sum(r['Volumes'] for r in raw),shares=8000,breadth={'quoted':80})
    other=dict(provider='Wafabourse',status='ok',session=DAY,scope='cash_equities',market_closed=True,
        observed_at='2026-10-23T18:00:00+00:00',source_url='https://www.wafabourse.com/marches',rows=secondary)
    return fixture,raw,overview,other,codes

class LocalMarketTests(unittest.TestCase):
    def test_adi_volume_conflict_publishes_exact_other_79(self):
        inp=universe();baseline=build_report(inp[0],'2026-10-23')
        adi=next(r for r in inp[3]['rows'] if r['symbol']==inp[4]['ADI']);adi['shares']+=1
        candidate,audit=reconcile_volumes(*inp,now=NOW,allow_local_isolation=True)
        self.assertEqual(audit['status'],'partial');self.assertEqual(audit['quarantined_symbols'],['ADI'])
        self.assertEqual(len(audit['validated_symbols']),79)
        corrected=deepcopy(inp[3]);next(r for r in corrected['rows'] if r['symbol']==inp[4]['ADI'])['shares']-=1
        recovered,recovery=reconcile_volumes(candidate,inp[1],inp[2],corrected,inp[4],now=NOW,allow_local_isolation=True)
        self.assertTrue(recovery['cross_source_verified'])
        self.assertNotIn('quarantined_market',recovered['records']['ADI'])
        report=build_report(candidate,'2026-10-23')
        original={r['symbol']:r for r in baseline['results']}
        for row in report['results']:
            if row['symbol']!='ADI':self.assertEqual(row,original[row['symbol']])
            else:
                self.assertIsNone(row['price']);self.assertIsNone(row['day_shares'])
                self.assertIsNone(row['technical']['sma20']);self.assertEqual(row['decision'],'INDISPONIBLE')
        report['market_overview']=inp[2];report['provenance']={'market_snapshot_sha256':'a'*64}
        audit['validated_snapshot_sha256']='a'*64;audit['providers'][0]['raw_sha256']='b'*64
        report['cross_source_volume_audit']=audit
        self.assertTrue(validated_local_scope(report,audit));self.assertFalse(audit_market_integrity(report)['failures'])
        next(r for r in report['results'] if r['symbol']=='ADI')['price']=999
        self.assertFalse(validated_local_scope(report,audit))

    def test_partial_volume_proof_survives_full_publication_gates(self):
        import argparse,shutil,tempfile
        from unittest.mock import patch
        import run
        from nour.market import atomic_json
        inp=universe();next(r for r in inp[3]['rows'] if r['symbol']==inp[4]['ADI'])['shares']+=1
        candidate,proof=reconcile_volumes(*inp,now=NOW,allow_local_isolation=True)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree(ROOT/'data',root/'data');output=root/'web';output.mkdir()
            atomic_json(root/'data/market_snapshot.json',candidate)
            proof['validated_snapshot_sha256']=hashlib.sha256((root/'data/market_snapshot.json').read_bytes()).hexdigest()
            for provider,payload in zip(proof['providers'],[inp[1],inp[3]]):provider['raw_sha256']=hashlib.sha256(json.dumps(payload).encode()).hexdigest()
            atomic_json(root/'data/market_integrity.json',proof)
            atomic_json(root/'data/market_overview.json',{'current':inp[2],'last_closed':inp[2]})
            atomic_json(root/'data/issuer_status.json',{'observed_asof':'2026-10-23','records':{}})
            with patch.object(run,'ROOT',root):run._build(argparse.Namespace(asof='2026-10-23',slot='refresh'),output)
            actual=json.loads((output/'report.json').read_text())
            self.assertEqual(len(list((output/'titres').glob('*.html'))),80)
            self.assertFalse(audit_market_integrity(actual)['failures'])
            self.assertEqual(len(actual['cross_source_volume_audit']['validated_symbols']),79)
            self.assertIsNone(next(r for r in actual['results'] if r['symbol']=='ADI')['price'])
            self.assertEqual(json.loads((output/'calculation-health.json').read_text())['status'],'degraded')

    def test_primary_bad_price_is_local_and_global_schema_is_not(self):
        inp=universe();raw=next(r for r in inp[1] if r['Symbol']==inp[4]['ADI']);raw['Cours']=None
        candidate,audit=isolate_market_lines(*inp,now=NOW)
        self.assertEqual(audit['quarantined_symbols'],['ADI']);self.assertEqual(len(audit['validated_symbols']),79)
        inp[1].append('bad general schema')
        with self.assertRaises(ValueError):isolate_market_lines(*inp,now=NOW)

    def test_import_adi_inconsistent_ohlc_does_not_stop_79_observations(self):
        inp=universe();raw=next(r for r in inp[1] if r['Symbol']==inp[4]['ADI']);raw['PlusHaut']=1
        candidate,details=import_session(inp[0],inp[1],inp[4],now=NOW)
        self.assertEqual(details['observations_refreshed'],79)
        self.assertEqual(details['conflicts'][0]['symbol'],'ADI')
        self.assertEqual(candidate['records']['ADI']['source_check_status'],'retained_conflict')

    def test_unavailable_source_reuses_only_original_matching_proof(self):
        inp=universe();_,proof=reconcile_volumes(*inp,now=NOW)
        report=build_report(inp[0],'2026-10-23');report['market_overview']=inp[2]
        report['provenance']={'market_snapshot_sha256':'a'*64};proof['validated_snapshot_sha256']='a'*64
        for provider in proof['providers']:provider['raw_sha256']='b'*64
        report['cross_source_volume_audit']=dict(status='retained_validated',publication_safe=True,last_valid_proof=proof)
        self.assertFalse(audit_market_integrity(report)['failures'])
        from nour.resilience import retained_market_context
        cache={'market':{'snapshot_sha256':'a'*64,'overview':inp[2],'proof':proof}}
        self.assertIsNotNone(retained_market_context('a'*64,cache,{'result':'error'}))
        self.assertIsNone(retained_market_context('c'*64,cache,{'result':'error'}))
        self.assertIsNone(retained_market_context('a'*64,cache,{'result':'updated'}))
        report['provenance']['market_snapshot_sha256']='c'*64
        self.assertTrue(audit_market_integrity(report)['failures'])
