from copy import deepcopy
import unittest
from nour.resilience import detached_intraday_proof

class DetachedProofTests(unittest.TestCase):
    def context(self):
        overview={'asof':'2026-10-23','status':'intraday','observed_at':'2026-10-23T15:33:00+00:00'}
        proof={'schema_version':1,'status':'intraday','publication_safe':True,'session':'2026-10-23',
               'observed_at':overview['observed_at'],'validated_snapshot_sha256':'a'*64}
        cache={'market':{'snapshot_sha256':'a'*64,'overview':deepcopy(overview),'proof':proof}}
        audit={'schema_version':1,'status':'detail_matched','publication_safe':True,'session':'2026-10-23',
               'validated_snapshot_sha256':'b'*64,'canonical_snapshot_sha256':'b'*64,
               'observed_at':'2026-10-23T18:00:00+00:00'}
        return 'a'*64,overview,cache,audit

    def test_exact_last_healthy_intraday_recovered_without_new_quote_or_clock(self):
        context=self.context();original=deepcopy(context);proof=detached_intraday_proof(*context)
        self.assertEqual(context,original)
        self.assertEqual(proof['observed_at'],'2026-10-23T15:33:00+00:00')
        self.assertEqual(proof['status'],'intraday')
        self.assertFalse(proof['restoration']['new_source_verification'])
        self.assertEqual(proof['restoration']['detached_snapshot_sha256'],'b'*64)

    def test_current_snapshot_refusal_is_never_overridden(self):
        for status in ('conflict','incomplete','unavailable','detail_matched'):
            c=self.context();c[3].update(status=status,validated_snapshot_sha256='a'*64,canonical_snapshot_sha256='a'*64)
            self.assertIsNone(detached_intraday_proof(*c))
        c=self.context();c[3]['publication_safe']=False
        self.assertIsNone(detached_intraday_proof(*c))

    def test_changed_snapshot_overview_session_or_proof_is_refused(self):
        for location,key,value in [(2,'snapshot_sha256','c'*64),(2,'proof',{}),(2,'overview',{}),
                                  (3,'session','2026-10-22'),(3,'schema_version',2),(3,'canonical_snapshot_sha256','c'*64)]:
            c=self.context();(c[2]['market'] if location==2 else c[3])[key]=value
            self.assertIsNone(detached_intraday_proof(*c))
        c=self.context();c[1]['status']='closed'
        self.assertIsNone(detached_intraday_proof(*c))

    def test_closed_cache_requires_existing_stronger_retention_path(self):
        c=self.context();c[2]['market']['proof']['status']='matched'
        self.assertIsNone(detached_intraday_proof(*c))
