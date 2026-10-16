"""Review queues and sector guardrails must never rewrite accounting outputs."""
import copy
import json
from pathlib import Path
import unittest

from nour.sector_audit import audit_sector_report


class SectorAuditTests(unittest.TestCase):
    def test_missing_document_and_review_queue_do_not_mutate_input(self):
        report = {"analysis_date": "2026-10-16", "results": [
            {"symbol": "ADI", "fundamental": {
                "document_url": "https://www.ammc.ma/a.pdf",
                "exercise": 2025, "evidence": {"chiffre_affaires": {"value": 2}},
                "financial_audit": {"status": "review_required", "blocked_metrics": []}}},
            {"symbol": "DIS", "fundamental": {
                "document_url": None, "evidence": {}, "financial_audit": {"status": "unavailable"}}},
        ]}
        before = copy.deepcopy(report)
        result = audit_sector_report(report)
        self.assertEqual(report, before)
        self.assertEqual(result["universe"], 2)
        self.assertEqual(result["review_states"]["missing_primary_document"], 1)
        self.assertEqual(result["review_states"]["primary_page_check_required"], 1)
        self.assertFalse(result["documents_certified"])
        self.assertEqual(result["violations"], [])

    def test_bank_and_insurance_industrial_debt_ratios_are_rejected(self):
        for symbol in ("ATW", "WAF"):
            report = {"results": [{"symbol": symbol, "fundamental": {
                "document_url": "https://example.org/a.pdf",
                "net_debt_ebitda": 2.0, "net_debt_strict_mmad": 100}}]}
            result = audit_sector_report(report)
            self.assertEqual(len(result["violations"]), 2)

    def test_invalid_claim_of_checked_primary_page_is_not_accepted(self):
        fact = {"page": 3, "document_url": "https://example.org/a.pdf",
                "period_end": "2025-12-31", "unit": "MMAD", "currency": "MAD",
                "document_hash": "sha256:" + "f" * 64, "accounting_basis": "consolidé",
                "validation_status": "selected_pages_visually_checked"}
        report = {"results": [{"symbol": "RIS", "fundamental": {
            "document_url": "https://example.org/a.pdf", "evidence": {"chiffre_affaires": fact},
            "financial_audit": {"status": "ok"}}}]}
        self.assertEqual(audit_sector_report(report)["selected_pages_reviewed_issuers"], 1)
        report["results"][0]["fundamental"]["evidence"]["chiffre_affaires"]["document_hash"] = None
        self.assertEqual(audit_sector_report(report)["selected_pages_reviewed_issuers"], 0)
        fact["document_hash"] = "sha256:" + "f" * 64
        fact["period_end"] = None
        self.assertEqual(audit_sector_report(report)["selected_pages_reviewed_issuers"], 0)

    def test_blocked_debt_reconciliation_is_a_priority_action_not_a_repair(self):
        comparison = {"status": "unresolved", "calculated_mmad": 1361.489,
                      "reported_mmad": 1303, "difference_mmad": 58.489,
                      "tolerance_mmad": 26.06}
        report = {"results": [{"symbol": "ADI", "fundamental": {
            "document_url": "https://www.ammc.ma/ADI_RFA_2025.pdf",
            "net_debt_strict_mmad": None, "financial_audit": {
                "status": "blocked", "blocked_metrics": ["net_debt_strict_mmad"],
                "debt_comparison": comparison,
                "checks": [{"code": "debt_arithmetic_mismatch", "status": "blocked",
                            "fields": ["dettes_financieres", "tresorerie_actif", "endettement_net"],
                            "blocked_metrics": ["net_debt_strict_mmad"]}]}}}]}
        before = copy.deepcopy(report)
        result = audit_sector_report(report)
        self.assertEqual(report, before)
        self.assertEqual(result["blocking_issuers"], 1)
        self.assertEqual(result["blocking_actions"], 1)
        self.assertEqual(result["review_queue"][0]["priority"], "P1")
        self.assertEqual(result["review_queue"][0]["debt_comparison_mmad"],\n                         {key: value for key, value in comparison.items() if key != "status"})
        self.assertIsNone(report["results"][0]["fundamental"]["net_debt_strict_mmad"])

    def test_checked_status_is_recognized_without_inventing_pdf_certification(self):
        fact = {"page": 3, "document_url": "https://example.org/a.pdf",
                "period_end": "2025-12-31", "unit": "MMAD", "currency": "MAD",
                "document_hash": "sha256:" + "a" * 64, "accounting_basis": "consolidé",
                "validation_status": "selected_pages_visually_checked"}
        report = {"results": [{"symbol": "RIS", "fundamental": {
            "document_url": "https://example.org/a.pdf",
            "evidence": {"chiffre_affaires": fact},
            "financial_audit": {"status": "checked", "checks": [], "blocked_metrics": []}}}]}
        result = audit_sector_report(report)
        self.assertEqual(result["review_states"]["selected_pages_checked"], 1)
        self.assertFalse(result["documents_certified"])

    def test_guidance_mismatch_is_violation(self):
        report = {"results": [{"symbol": "ATW", "sector_guidance": {"family": "Tourisme"},
                               "fundamental": {"document_url": None}}]}
        self.assertEqual(len(audit_sector_report(report)["violations"]), 1)


if __name__ == "__main__":
    unittest.main()
