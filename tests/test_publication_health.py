"""Independent publication arithmetic refuses silently inconsistent exports."""
import copy
import unittest
from tools.audit_readiness import publication_health


def report():
    evidence = {k: dict(value=v, unit=u) for k,v,u in (
        ('resultat_net_part_groupe',10,'MMAD'),
        ('capitaux_propres_part_groupe',100,'MMAD'),
        ('nombre_actions',1000000,'actions'))}
    fundamental = dict(evidence=evidence, exercise=2025, eps_mad=10,
        book_value_per_share_mad=100, pe=2, pb=.2, roe_pct=10,
        validation_status='referenced_import', financial_audit={'version':'test'})
    return dict(analysis_date='2026-10-16',snapshot_updated='2026-10-15',
        source_commit='fixture',fundamental_coverage={},results=[dict(
            symbol='TEST',price=20,fundamental=fundamental,
            canonical_score=dict(value=50,state='CALCULABLE',contributors={'a':dict(weight=20,points=10)},
                                 nlp_weight=0))])


class PublicationHealth(unittest.TestCase):
    def test_recomputes_before_publishing_without_certifying_documents(self):
        r=report();before=copy.deepcopy(r);h=publication_health(r)
        self.assertEqual(h['status'],'arithmetic_checked')
        self.assertFalse(h['documents_certified'])
        self.assertEqual(h['issuer_controls']['TEST']['version'],'test')
        self.assertEqual(h['failures'],[])
        self.assertEqual(r,before)

    def test_wrong_eps_and_score_are_reported_independently(self):
        r=report();r['results'][0]['fundamental']['eps_mad']=10000
        r['results'][0]['canonical_score']['value']=99
        h=publication_health(r)
        self.assertEqual(h['status'],'blocked')
        self.assertEqual({f['metric'] for f in h['failures']},{'eps_mad','score'})

    def test_missing_ratio_is_not_imputed(self):
        r=report();r['results'][0]['fundamental']['pe']=None
        h=publication_health(r)
        self.assertEqual(h['failures'],[])
        self.assertIsNone(r['results'][0]['fundamental']['pe'])

    def test_dirham_dividend_alias_uses_same_arithmetic_contract(self):
        r=report();f=r['results'][0]['fundamental']
        f['evidence']['dividende_par_action']=dict(value=1,unit='MAD')
        f['dividend_yield_pct']=5
        self.assertEqual(publication_health(r)['failures'],[])
