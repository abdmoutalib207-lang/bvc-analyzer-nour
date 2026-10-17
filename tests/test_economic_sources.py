"""Economic context sources are not evidence for issuer financial ratios."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from nour.economic_sources import load_catalog, catalog_page, catalog_summary


class EconomicSourceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_registry_covers_user_requested_economic_institutions(self):
        self.assertEqual(len(self.catalog["institutions"]), 36)
        ids = {item["id"] for item in self.catalog["institutions"]}
        self.assertTrue({"AMMC", "MAROCLEAR", "ACAPS", "BAM", "HCP",
                         "OFFICE_CHANGES", "ONDA", "ANP", "OCP",
                         "ONEE", "MEF", "DEPP", "TGR", "COUR_COMPTES"} <= ids)

    def test_context_cannot_become_issuer_accounting_evidence(self):
        self.assertFalse(self.catalog["usable_for_score"])
        self.assertFalse(self.catalog["usable_to_certify_issuer_financial_facts"])
        for item in self.catalog["institutions"]:
            self.assertFalse(item["automatic_import"])
            self.assertEqual(item["issuer_accounting_fact_authority"],
                             item["role"] == "issuer_document")
        summary = catalog_summary(self.catalog)
        self.assertFalse(summary["auto_import_enabled"])
        self.assertEqual(summary["institution_count"], 36)

    def test_duplicate_and_unsafe_urls_rejected(self):
        for change in ("duplicate", "unsafe", "unauthorized"):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.catalog)
                if change == "duplicate":
                    altered["institutions"].append(copy.deepcopy(altered["institutions"][0]))
                elif change == "unsafe":
                    altered["institutions"][0]["url"] = "http://not-official.example"
                else:
                    altered["institutions"][4]["issuer_accounting_fact_authority"] = True
                with tempfile.TemporaryDirectory() as directory:
                    file = Path(directory) / "sources.json"
                    file.write_text(json.dumps(altered), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_catalog(file)

    def test_html_escapes_untrusted_registry_fields(self):
        altered = copy.deepcopy(self.catalog)
        altered["institutions"][0]["name"] = '<script>alert("bad")</script>'
        page = catalog_page(altered)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("Aucune donnée de ce registre", page)


if __name__ == "__main__":
    unittest.main()
