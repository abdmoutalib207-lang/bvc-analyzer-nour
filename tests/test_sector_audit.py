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
        self.assertEqual(result["review_queue"][0]["debt_comparison_mmad"],
                         {key: value for key, value in comparison.items() if key != "status"})
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

    def test_present_but_unverified_fact_is_not_counted_as_primary_checked(self):
        fact = {"page": 15, "value": 99, "unit": "MMAD",
                "document_url": "https://example.org/bank.pdf",
                "accounting_basis": "consolidé", "period_end": "2025-12-31",
                "currency": "MAD", "validation_status": "referenced_import",
                "document_hash": None}
        report = {"results": [{"symbol": "ATW", "fundamental": {
            "document_url": "https://example.org/bank.pdf",
            "evidence": {"produit_net_bancaire": fact, "resultat_net_part_groupe": fact},
            "financial_audit": {"status": "checked"}}}]}
        result = audit_sector_report(report)
        row = result["issuers"][0]
        self.assertEqual(row["selected_page_evidence_count"], 0)
        self.assertEqual(row["missing_annual_fact_groups"], [])
        self.assertEqual(len(row["unverified_annual_fact_groups"]), 2)
        self.assertEqual(row["status"], "primary_page_check_required")

    def test_tgcc_sgtm_cmgp_consolidated_total_is_not_group_profit(self):
        from nour.fundamentals import calculate
        facts = json.loads((Path(__file__).resolve().parents[1] / "data/facts_reference.json").read_text())["records"]
        for symbol in ("TGCC", "SGTM", "CMGP"):
            with self.subTest(symbol=symbol):
                # Reproduce the unresolved pre-review dossier: a later primary
                # import must not weaken the total-versus-group guardrail.
                unresolved = copy.deepcopy(facts[symbol])
                unresolved['faits'] = copy.deepcopy(unresolved.get('reconciliation_prior_oct18', unresolved['faits']))
                unresolved.pop('calculation_reservations', None)
                result = calculate({"symbol": symbol, "price": 200}, unresolved, asof="2026-10-16")
                self.assertIn("resultat_net_consolide", result["evidence"])
                self.assertIsNone(result["eps_mad"])
                self.assertIsNone(result["pe"])
                self.assertIsNone(result["roe_pct"])
                checks = result["financial_audit"]["checks"]
                self.assertTrue(any(check["code"] == "group_earnings_missing_total_not_substituted"
                                    and check["status"] == "blocked" for check in checks))
                report = {"results": [{"symbol": symbol, "fundamental": result}]}
                actions = audit_sector_report(report)["review_queue"]
                self.assertTrue(any(a["code"] == "group_earnings_missing_total_not_substituted"
                                    and a["source_pages_to_check"] for a in actions))

    def test_guidance_mismatch_is_violation(self):
        report = {"results": [{"symbol": "ATW", "sector_guidance": {"family": "Tourisme"},
                               "fundamental": {"document_url": None}}]}
        self.assertEqual(len(audit_sector_report(report)["violations"]), 1)


if __name__ == "__main__":
    unittest.main()
