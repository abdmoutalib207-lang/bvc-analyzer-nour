"""A wrong aggregate cannot certify the market or freeze independently checked titles."""
import copy
import unittest
from nour.volume_guard import reconcile_volumes
from nour.market_integrity import validated_detail_scope, visible_integrity, integrity_summary
from nour.market_view import market_panel
from tools.audit_market_integrity import audit_market_integrity
from test_volume_guard import observations, NOW, DAY


def detail_case():
    inputs=observations()
    inputs[2].update(turnover_mad='544.03',shares=41,breadth={'quoted':3})
    fixture,audit=reconcile_volumes(*inputs,now=NOW,minimum=2,allow_detail_only=True)
    audit['validated_snapshot_sha256']='a'*64
    for idx,provider in enumerate(audit['providers']):
        provider['raw_sha256']=str(idx+1)*64
    overview=copy.deepcopy(inputs[2]);overview['turnover_mad']=float(overview['turnover_mad'])
    report={'analysis_date':DAY,'market_overview':overview,
            'provenance':{'market_snapshot_sha256':'a'*64},'cross_source_volume_audit':audit,
            'results':[{'symbol':s,'asof':r['price_asof'],'price':r['price'],
                        'day_turnover_mad_actual':r['day_turnover_mad'],'day_shares':r['day_shares']}
                       for s,r in fixture['records'].items()]}
    return inputs,report,audit


class DetailScope(unittest.TestCase):
    def test_only_exact_two_provider_detail_is_publishable_with_global_reservation(self):
        inputs=observations();inputs[2].update(turnover_mad='544.03',shares=41,breadth={'quoted':3})
        before=copy.deepcopy(inputs)
        fixture,audit=reconcile_volumes(*inputs,now=NOW,minimum=2,allow_detail_only=True)
        self.assertEqual(fixture,inputs[0]);self.assertEqual(inputs,before)
        self.assertEqual(audit['status'],'detail_matched');self.assertFalse(audit['aggregate_match'])
        self.assertEqual(audit['publication_scope'],'validated_title_lines')
        self.assertEqual(audit['totals']['cdg_overview']['turnover_mad'],'544.03')
        self.assertEqual(audit['totals']['retained_after']['turnover_mad'],'500.03')
        self.assertEqual(audit['corrections'],[])
        self.assertEqual(audit['refusals'][0]['code'],'reported_aggregate_mismatch')

    def test_missing_quantities_outage_bad_prices_or_pending_revisions_still_refuse(self):
        for mutate in (lambda x:x[3]['rows'][0].update(shares=None),
                       lambda x:x[3].update(status='timeout'),
                       lambda x:x[3]['rows'][0].update(price=11),
                       lambda x:x[0]['records']['AAA'].update(day_shares=9),
                       lambda x:x[3]['rows'].pop()):
            inputs=observations();inputs[2].update(turnover_mad='544.03',shares=41,breadth={'quoted':3});mutate(inputs)
            before=copy.deepcopy(inputs)
            fixture,audit=reconcile_volumes(*inputs,now=NOW,minimum=2,allow_detail_only=True)
            self.assertFalse(audit['publication_safe']);self.assertEqual(fixture,before[0]);self.assertEqual(inputs,before)

    def test_public_gate_accepts_exact_detail_proof_without_certifying_aggregate(self):
        _,report,audit=detail_case()
        self.assertTrue(validated_detail_scope(report,audit))
        self.assertEqual(visible_integrity(audit,report)['status'],'detail_matched')
        result=audit_market_integrity(report)
        self.assertEqual(result['failures'],[]);self.assertEqual(result['status'],'checked_with_reservations')
        self.assertEqual(result['internal']['status'],'incomplete')
        self.assertEqual(result['internal']['lines_shares'],30)
        self.assertIn('Total global non confirmé',market_panel(report))
        self.assertIn('44,00 MAD',market_panel(report))
        self.assertEqual(integrity_summary(audit)['publication_scope'],'validated_title_lines')

    def test_missing_or_forged_proof_cannot_escape_the_gate(self):
        for mutate in (lambda r,a:a.pop('validated_lines'),
                       lambda r,a:a.update(corrections=[{'symbol':'AAA'}]),
                       lambda r,a:a.update(proposed_corrections=[{'symbol':'AAA'}]),
                       lambda r,a:a.update(quantities_cross_source_verified=False),
                       lambda r,a:a.update(validated_snapshot_sha256='b'*64),
                       lambda r,a:a['providers'][1].update(source_url=a['providers'][0]['source_url']),
                       lambda r,a:a['totals']['secondary'].update(shares=31),
                       lambda r,a:a['totals']['cdg_overview'].update(quoted=2),
                       lambda r,a:r['results'][0].update(price=11),
                       lambda r,a:r['results'][0].update(day_shares=11),
                       lambda r,a:a.update(validated_symbols=['AAA']),
                       lambda r,a:a.update(aggregate_match=True)):
            _,report,audit=detail_case();mutate(report,audit)
            self.assertFalse(validated_detail_scope(report,audit))
            self.assertEqual(audit_market_integrity(report)['status'],'blocked')
            self.assertEqual(visible_integrity(audit,report)['status'],'stale')
