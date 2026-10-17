"""The métier review is visible, source-aware and HTML-escaped."""
import unittest

from nour.site import sector_page


class SectorPageTests(unittest.TestCase):
    def test_page_shows_distinct_bank_and_hotel_and_source_limitations(self):
        report = {"snapshot_updated": "2026-10-16T16:00:00",
                  "results": [
                      {"symbol": "ATW", "fundamental": {
                          "document_url": "https://www.ammc.ma/bank.pdf",
                          "evidence": {}, "financial_audit": {"status": "review_required"}}},
                      {"symbol": "RIS", "fundamental": {
                          "document_url": None, "evidence": {},
                          "financial_audit": {"status": "unavailable"}}},
                  ]}
        page = sector_page(report, "", "")
        for needle in ("Analyse par métier", "PNB", "RevPAR", "ATW", "RIS",
                       "Document primaire absent", "Document ↗",
                       "sector-readiness.json", "ne certifie pas un rapport entier"):
            self.assertIn(needle, page)

    def test_untrusted_document_url_is_escaped(self):
        report = {"results": [{"symbol": "ADI", "fundamental": {
            "document_url": 'https://example.org/?x=" onmouseover="alert(1)',
            "evidence": {}, "financial_audit": {"status": "review_required"}}}]}
        page = sector_page(report, "", "")
        self.assertNotIn('onmouseover="alert(1)', page)
        self.assertIn('&quot;', page)


if __name__ == "__main__":
    unittest.main()
