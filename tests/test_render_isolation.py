import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nour.site import build_site,detail_page
from tools.audit_site import audit
ROOT=Path(__file__).resolve().parents[1]

class RenderIsolation(unittest.TestCase):
    def test_one_issuer_template_failure_keeps_other_79_pages_and_report(self):
        fixture=json.loads((ROOT/'data/market_snapshot.json').read_text())
        report=json.loads((ROOT/'web/report.json').read_text())
        original={r['symbol']:{k:r[k] for k in ('technical','fundamental','canonical_score')} for r in report['results']}
        def broken(item,*args,**kwargs):
            if item['symbol']=='RDS':raise RuntimeError('template injection')
            return detail_page(item,*args,**kwargs)
        with tempfile.TemporaryDirectory() as d,patch('nour.site.detail_page',side_effect=broken):
            out=Path(d)
            build_site(fixture,report,out)
            self.assertEqual(len(list((out/'titres').glob('*.html'))),80)
            self.assertIn('Fiche indisponible',(out/'titres/RDS.html').read_text())
            self.assertIn('data-bi-dashboard',(out/'titres/ADI.html').read_text())
            actual=json.loads((out/'report.json').read_text())
            for row in actual['results']:
                self.assertEqual({k:row[k] for k in ('technical','fundamental','canonical_score')},original[row['symbol']])
                self.assertEqual(row['page_render_status'],'unavailable' if row['symbol']=='RDS' else 'available')
            audit(out)
