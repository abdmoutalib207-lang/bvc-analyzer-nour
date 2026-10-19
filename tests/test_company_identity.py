import json
from pathlib import Path
import unittest
from nour.company_identity import catalog, company_logo, validate_catalog, validate_svg
from nour.source_view import market_sources


class CompanyIdentity(unittest.TestCase):
    def test_catalog_matches_universe_and_real_files_are_safe(self):
        root = Path(__file__).resolve().parents[1]
        symbols = json.loads((root/'data/market_snapshot.json').read_text())['symbols']
        validate_catalog(symbols)
        self.assertEqual(len(catalog()),80)
        for symbol,mark in catalog().items():
            if mark['status']!='verified':self.assertNotIn('src=',company_logo(symbol))
        self.assertIn('../logos/ADI.svg',company_logo('ADI','../'))

    def test_external_or_active_svg_is_rejected(self):
        for payload in [b'<svg><script/></svg>',b'<svg><image href="https://example.org/logo.png"/></svg>',
                        b'<svg onload="bad()"/>',b'<!DOCTYPE svg><svg/>',b'<svg><foreignObject/></svg>']:
            with self.assertRaises(ValueError):validate_svg(payload)
        validate_svg(b'<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(#a)" d="M0 0"/></svg>')

    def test_attribution_stays_exact_in_central_source_space(self):
        report={'market_overview':{'source':'CDG Capital Bourse','source_url':'https://www.cdgcapitalbourse.ma/Bourse/market','asof':'2026-10-16'},
                'results':[{'price_source':'CDG Capital Bourse'}]}
        body=market_sources(report)
        self.assertIn('id="marche"',body)
        self.assertIn('CDG Capital Bourse',body)
        self.assertIn('https://www.cdgcapitalbourse.ma/Bourse/market',body)
        self.assertEqual(report['results'][0]['price_source'],'CDG Capital Bourse')
