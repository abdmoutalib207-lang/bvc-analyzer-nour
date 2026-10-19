import copy
import json
from pathlib import Path
import unittest
from nour.market_reference import apply_market_reference, reviewed_reference
from nour.market_view import market_panel, closing_summary
from tools.audit_market_integrity import audit_market_integrity


class MarketReference(unittest.TestCase):
    def setUp(self):
        self.reference=json.loads((Path(__file__).resolve().parents[1]/'data/market_reference.json').read_text())
        self.market={'asof':'2026-10-19','status':'closed','source_url':'https://www.cdgcapitalbourse.ma/Bourse/market',
                     'turnover_mad':113956983.12,'shares':876356,'transactions':2851,'breadth':{'quoted':62}}

    def test_index_date_does_not_certify_counter_or_change_original_observation(self):
        before=copy.deepcopy(self.market)
        result=apply_market_reference(self.market,{})
        self.assertIsNone(result['transactions']);self.assertEqual(result['transactions_reported'],2851)
        self.assertNotIn('official_reference',result)
        self.assertEqual(apply_market_reference(result,{}),result)
        self.assertEqual(self.market,before)

    def test_reviewed_capture_is_same_session_and_keeps_distinct_contract_label(self):
        before=copy.deepcopy(self.reference)
        result=apply_market_reference(self.market,self.reference)
        self.assertEqual(result['official_reference']['contracts'],3671)
        self.assertEqual(result['transactions_reported'],2851);self.assertIsNone(result['transactions'])
        self.assertEqual(result['official_reference']['review_status'],'manual_capture_reviewed')
        self.assertEqual(self.reference,before)
        report={'analysis_date':'2026-10-19','market_overview':result,'results':[]}
        page=market_panel(report)
        self.assertIn('Contrats · référence officielle',page)
        self.assertIn('3 671',page);self.assertIn('2 851',page)
        self.assertIn('date propre n’est pas attestée',page)
        self.assertIn('capture revue manuellement',closing_summary(result))

    def test_old_capture_cannot_relabel_a_new_session_or_different_aggregate(self):
        for mutate in (lambda m:m.update(asof='2026-10-20'),
                       lambda m:m.update(turnover_mad=113956939.12),
                       lambda m:m.update(shares=876345)):
            m=copy.deepcopy(self.market);mutate(m)
            self.assertIsNone(reviewed_reference(m,self.reference))
            self.assertNotIn('official_reference',apply_market_reference(m,self.reference))

    def test_malformed_or_unreviewed_reference_is_rejected(self):
        for change in ({'asof':'2026-10-16'},{'review_status':'detected'},
                       {'source_url':'https://evil.example/market-data/volume'},
                       {'source_url':'https://www.casablanca-bourse.com/market-data/volume?token=secret'},
                       {'capture_sha256':'bad'},{'reviewed_at':'2026-10-19T18:40:00'},
                       {'contracts':True},{'contracts':-1},{'contracts':3.5},{'contracts':'3671'},
                       {'contracts':float('nan')},{'shares':True},{'turnover_mad':float('inf')}):
            reference=copy.deepcopy(self.reference);reference['sessions']['2026-10-19'].update(change)
            self.assertIsNone(reviewed_reference(self.market,reference))

    def test_final_gate_rejects_forged_official_proof_or_undated_counter(self):
        from test_detail_scope import detail_case
        _,report,_=detail_case()
        report['market_overview']['official_reference']={'asof':report['market_overview']['asof']}
        self.assertEqual(audit_market_integrity(report)['status'],'blocked')
        _,report,_=detail_case()
        report['market_overview'].update(transactions=2851,transactions_quality={'status':'unverified'})
        self.assertEqual(audit_market_integrity(report)['status'],'blocked')
