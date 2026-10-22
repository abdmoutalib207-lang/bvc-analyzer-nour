"""Exact primary-only publication is useful, but never a multisource proof."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from test_volume_guard import observations, NOW
from nour.volume_guard import reconcile_volumes
from nour.market_integrity import validated_primary_scope, visible_integrity
from nour.market_view import market_panel
from nour.secondary_market import parse_wafabourse, ACTION
from tools.audit_market_integrity import audit_market_integrity


class PrimaryPublication(unittest.TestCase):
    def report(self, status='invalid'):
        fixture, lines, overview, secondary, codes=observations()
        secondary.update(status=status, rows=[], session=None)
        candidate, audit=reconcile_volumes(fixture,lines,overview,secondary,codes,now=NOW,minimum=2)
        self.assertEqual(candidate,fixture)
        overview['turnover_mad']=float(overview['turnover_mad'])
        audit['validated_snapshot_sha256']='c'*64
        for p in audit['providers']:
            p['raw_sha256']='a'*64
        return {'analysis_date':'2026-10-18','market_overview':overview,
                'provenance':{'market_snapshot_sha256':'c'*64},
                'results':[{'symbol':s,'asof':r['price_asof'],'price':r['price'],
                            'day_shares':r['day_shares'],'day_turnover_mad_actual':r['day_turnover_mad']}
                           for s,r in fixture['records'].items()],
                'cross_source_volume_audit':audit}

    def test_unchanged_primary_exact_totals_and_visible_reservations(self):
        for status in ('invalid','timeout','error','unavailable'):
            r=self.report(status);a=r['cross_source_volume_audit']
            self.assertTrue(validated_primary_scope(r,a))
            self.assertFalse(a['cross_source_verified'])
            self.assertFalse(a['quantities_cross_source_verified'])
            self.assertEqual(audit_market_integrity(r)['status'],'checked_with_reservations')
            html=market_panel(r)
            self.assertIn('data-market-integrity="primary-only"',html)
            self.assertIn('ne constitue pas une validation entre deux fournisseurs',html)

    def test_forged_proof_stale_snapshot_or_changed_rows_block(self):
        changes=[
            lambda r:r['provenance'].update(market_snapshot_sha256='d'*64),
            lambda r:r['market_overview'].update(asof='2026-10-15'),
            lambda r:r['market_overview'].update(status='intraday'),
            lambda r:r['market_overview'].update(turnover_mad=999),
            lambda r:r['market_overview'].update(shares=29),
            lambda r:r['market_overview']['breadth'].update(quoted=3),
            lambda r:r['results'][0].update(price=11),
            lambda r:r['results'][0].update(day_shares=9),
            lambda r:r['results'][0].update(day_turnover_mad_actual=99),
            lambda r:r['results'].append(deepcopy(r['results'][0])),
            lambda r:r['results'].pop(),
            lambda r:r['cross_source_volume_audit'].update(cross_source_verified=True),
            lambda r:r['cross_source_volume_audit'].update(quantities_cross_source_verified=True),
            lambda r:r['cross_source_volume_audit'].update(corrections=[{'symbol':'AAA'}]),
            lambda r:r['cross_source_volume_audit'].update(proposed_corrections=[{'symbol':'AAA'}]),
            lambda r:r['cross_source_volume_audit'].update(refusals=[{'reason':'contradiction'}]),
            lambda r:r['cross_source_volume_audit'].update(secondary_status='ok'),
            lambda r:r['cross_source_volume_audit'].update(observed_at='2026-10-15T20:00:00+00:00'),
            lambda r:r['cross_source_volume_audit'].update(observed_at='2026-10-19T20:00:00+00:00'),
            lambda r:r['cross_source_volume_audit'].update(observed_at='2026-10-16T12:00:00+00:00'),
            lambda r:r['cross_source_volume_audit']['providers'][0].update(raw_sha256=''),
            lambda r:r['cross_source_volume_audit']['validated_lines']['AAA'].update(price=True),
            lambda r:r['cross_source_volume_audit']['totals']['retained_before'].update(shares=29),
        ]
        for change in changes:
            with self.subTest(change=change):
                r=self.report();change(r);a=r['cross_source_volume_audit']
                self.assertFalse(validated_primary_scope(r,a))
                self.assertTrue(audit_market_integrity(r)['failures'])
                self.assertEqual(visible_integrity(a,r)['status'],'stale')

    def test_real_second_provider_contradictions_never_downgraded(self):
        for field,value in (('price',11),('amount_mad',90),('shares',9)):
            inputs=observations();inputs[3]['rows'][0][field]=value
            candidate,audit=reconcile_volumes(*inputs,now=NOW,minimum=2)
            self.assertEqual(audit['status'],'conflict')
            self.assertFalse(audit['publication_safe'])
            self.assertEqual(candidate,inputs[0])
        for change in (lambda x:x[0]['records']['AAA'].update(day_shares=9),
                       lambda x:x[2].update(turnover_mad=999)):
            inputs=observations();inputs[3]['status']='invalid';change(inputs)
            candidate,audit=reconcile_volumes(*inputs,now=NOW,minimum=2,allow_detail_only=True)
            self.assertFalse(audit['publication_safe'])
            self.assertEqual(candidate,inputs[0])

    def test_placeholder_date_is_explicit_not_imputed(self):
        row=dict(IdTypeValeur=1,Symbol='ALM',Etat='Market Close',Volumes=3720,Cours=1860,
                 QteEchangee=2,DateDernierCours='01/01/1900 10:17:00')
        source=parse_wafabourse([{ACTION:{'Valid':True,'Data':[row]}}],
                               observed_at='2026-10-22T20:00:00+00:00',expected_session='2026-10-22')
        self.assertEqual(source['status'],'invalid')
        self.assertIsNone(source['session'])
        self.assertEqual(source['rows'],[])
        self.assertTrue(any('ALM' in n and '1900' in n for n in source['notices']))
