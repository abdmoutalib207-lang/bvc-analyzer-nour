import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from nour.history_import import reconcile
from nour.issuer_status import apply_status
from nour.engine import build_report

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a'*40


def bar(d, c=10, v=5):
    return dict(d=d, o=c, h=c, l=c, c=c, v=v)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'pipeline/candles').mkdir(parents=True)
        (self.root/'datasets/historiques_importes').mkdir(parents=True)
        self.fixture = {'symbols': ['ABC','CMT'], 'records': {
            'ABC': {'candles': [bar('2026-09-21', 20), bar('2026-10-05', 40)], 'price': 40, 'legacy_sig': 'untouched'},
            'CMT': {'candles': [bar('2026-09-21')], 'resumed_recently': True}}}
        self.manifest = dict(ticker='ABC', code_operateur='AB', sha256_fichier_recu='c'*64,
                             periode_source=['2026-09-21','2026-09-25'])
        self.write([bar('2026-09-21'), bar('2026-09-22', v=0), bar('2026-10-05', 90)])

    def write(self, bars):
        (self.root/'pipeline/candles/ABC.json').write_text(json.dumps(bars))
        (self.root/'datasets/historiques_importes/ABC.json').write_text(json.dumps(self.manifest))

    def run_import(self):
        return reconcile(self.fixture,self.root,{'ABC':'AB'},'2026-10-18',SHA,SHA)

    def test_export_replaces_legacy_but_preserves_recent_and_resumption(self):
        before=deepcopy(self.fixture)
        result,audit=self.run_import()
        self.assertEqual(result['records']['ABC']['candles'],[bar('2026-09-21'),bar('2026-09-22',v=0),bar('2026-10-05',40)])
        self.assertEqual((audit['added'],audit['replaced']),(1,1))
        self.assertEqual(audit['issuers'][0]['recent_observations_retained'][0]['fields'],['o','h','l','c'])
        self.assertEqual(result['records']['CMT'],before['records']['CMT'])
        self.assertEqual(self.fixture,before)
        self.assertEqual(result['records']['ABC']['legacy_sig'],'untouched')
        again,second=reconcile(result,self.root,{'ABC':'AB'},'2026-10-18',SHA,SHA)
        self.assertEqual(again,result)
        self.assertEqual(second['changed_issuers'],0)

    def test_older_manifest_schema_is_explicitly_supported(self):
        self.manifest['periode']=self.manifest.pop('periode_source')
        self.write([bar('2026-09-21')])
        self.assertEqual(self.run_import()[1]['replaced'],1)

    def test_newer_export_quote_remains_dated_and_has_no_invented_turnover(self):
        self.fixture['records']['ABC'].update(candles=[bar('2026-09-21')],price=10,price_asof='2026-09-21',stale=True)
        self.write([bar('2026-09-21'),bar('2026-09-22',11)])
        result,audit=self.run_import();r=result['records']['ABC']
        self.assertEqual((r['price'],r['price_asof']),(11,'2026-09-22'))
        self.assertIsNone(r['day_turnover_mad'])
        self.assertTrue(r['stale'])
        self.assertEqual(audit['issuers'][0]['quote_alignment']['previous_date'],'2026-09-21')

    def test_operator_identity_and_hash_required(self):
        for field,value in [('ticker','OTHER'),('code_operateur','OTHER'),('sha256_fichier_recu','bad')]:
            with self.subTest(field=field):
                old=self.manifest[field];self.manifest[field]=value;self.write([])
                with self.assertRaises(ValueError):self.run_import()
                self.manifest[field]=old

    def test_duplicates_refused(self):
        self.write([bar('2026-09-21'),bar('2026-09-21')])
        with self.assertRaises(ValueError):self.run_import()

    def test_invalid_source_is_not_used_or_allowed_to_delete_legacy(self):
        invalid=bar('2026-09-21');invalid['h']=1
        self.write([invalid,bar('2026-10-19'),bar('2026-09-17'),bar('2026-09-26')])
        result,audit=self.run_import()
        self.assertEqual(result['records']['ABC']['candles'],self.fixture['records']['ABC']['candles'])
        self.assertIn('2026-09-21',audit['issuers'][0]['rejected_source_dates'])


class IssuerStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((ROOT/'data/market_snapshot.json').read_text())
        cls.registry=json.loads((ROOT/'data/issuer_status.json').read_text())

    def test_known_suspensions_are_not_current_prices_or_collection_failures(self):
        f=apply_status(self.fixture,self.registry,'2026-10-18')
        report=build_report(f,asof='2026-10-18')
        rows={r['symbol']:r for r in report['results']}
        for s in ('DIS','DLM'):
            self.assertEqual(rows[s]['decision'],'SUSPENDU')
            self.assertIsNone(rows[s]['price'])
            self.assertIsNone(rows[s]['asof'])
            self.assertIn('absence de transactions documentée',rows[s]['history_readiness']['label'])
            self.assertNotIn('Désaccord',' '.join(rows[s]['quality']['issues']))
            self.assertIsNone(rows[s]['fundamental']['pe'])
        self.assertEqual(rows['IBM']['price'],self.fixture['records']['IBM']['price'])
        self.assertEqual(rows['IBM']['issuer_status']['trading_status'],'listed')
        self.assertEqual(report['fundamental_coverage']['current_universe'],78)
        self.assertEqual(set(report['fundamental_coverage']['archived_symbols']),{'DIS','DLM'})

    def test_status_is_dated_and_does_not_mutate_source(self):
        before=deepcopy(self.fixture)
        self.assertEqual(apply_status(self.fixture,self.registry,'2026-10-15'),before)
        apply_status(self.fixture,self.registry,'2026-10-18')
        self.assertEqual(self.fixture,before)
