"""Independent sector-by-sector evidence inventory, not a source of new ratios.

Runs over the already-computed Nour report. Never overwrites a fundamental,
a market price or a canonical score. No external fetch and no PDF certification.
"""
from collections import Counter
import re

from .sector_methods import guidance

HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
CHECKED = frozenset({
    "selected_pages_visually_checked",
    "selected_pages_reconciled_with_reservations_2026-10-05",
    "pdf_page_visually_checked_2026-10-04",
    "historical_closing_shares_visually_checked",
})
# This is a *review queue*, not an assertion that these KPI are always disclosed.
DOCUMENT_CHECKLIST = {
    "Banque": (("produit_net_bancaire",), ("resultat_net_part_groupe", "resultat_net_social")),
    "Assurance": (("resultat_net_part_groupe", "resultat_net_social"),),
    "Immobilier - promotion": (("chiffre_affaires",), ("resultat_net_part_groupe", "resultat_net_social")),
    "BTP et ingénierie": (("chiffre_affaires",), ("resultat_net_part_groupe", "resultat_net_social")),
    "Tourisme et hôtellerie": (("chiffre_affaires",),),
    "Santé et distribution médicale": (("chiffre_affaires",),),
    "Agriculture et intrants": (("chiffre_affaires",),),
    "Ports et logistique": (("chiffre_affaires",),),
    "Mines": (("chiffre_affaires",),),
    "Technologie et services": (("chiffre_affaires",),),
}
# These are institution-specific accounting incompatibilities, not
# cross-sector rankings. Other financial services need individual review.
NON_INDUSTRIAL_DEBT_FAMILIES = frozenset(("Banque", "Assurance"))


def _primary_checked(fact):
    if not isinstance(fact, dict):
        return False
    return (fact.get("validation_status") in CHECKED
            and isinstance(fact.get("page"), int) and not isinstance(fact["page"], bool)
            and fact["page"] > 0
            and isinstance(fact.get("document_url"), str)
            and fact["document_url"].startswith("https://")
            and isinstance(fact.get("document_hash"), str)
            and HASH.fullmatch(fact["document_hash"]) is not None
            and bool(fact.get("accounting_basis")))


def audit_sector_report(report):
    """Return an auditable issuer queue. 'No violations' is not certification."""
    issuers, violations = [], []
    for row in report.get("results", []):
        symbol = row["symbol"]
        f = row.get("fundamental") or {}
        method = guidance(symbol, {"sector": row.get("sector")})
        family = method["family"]
        evidence = f.get("evidence") or {}
        checked = [key for key, fact in evidence.items() if _primary_checked(fact)]
        required = DOCUMENT_CHECKLIST.get(family, ())
        missing = ["/".join(alternatives) for alternatives in required
                   if not any(key in evidence for key in alternatives)]
        audit = f.get("financial_audit") or {}
        audit_status = audit.get("status", "unavailable")
        if family in NON_INDUSTRIAL_DEBT_FAMILIES:
            for metric in ("net_debt_ebitda", "net_debt_strict_mmad"):
                if f.get(metric) is not None:
                    violations.append({"symbol": symbol, "metric": metric,
                                       "issue": "non-industrial debt ratio presented for bank/insurer"})
        if row.get("sector_guidance") is not None and row["sector_guidance"] != method:
            violations.append({"symbol": symbol, "issue": "sector guidance diverges from canonical taxonomy"})
        source = f.get("document_url")
        if not source:
            status = "missing_primary_document"
        elif audit_status == "blocked":
            status = "financial_audit_blocked"
        elif not checked:
            status = "primary_page_check_required"
        elif missing or audit_status != "ok":
            status = "additional_review_required"
        else:
            status = "selected_pages_checked"
        issuers.append({
            "symbol": symbol,
            "family": family,
            "classification": method["coverage"],
            "status": status,
            "financial_audit_status": audit_status,
            "document_url": source,
            "annual_exercise": f.get("exercise"),
            "evidence_count": len(evidence),
            "selected_page_evidence_count": len(checked),
            "missing_annual_fact_groups": missing,
            "business_kpis_to_collect": method["metrics_to_verify"],
            "accounting_exclusions": method["invalid_shortcuts"],
            "blocked_metrics": audit.get("blocked_metrics") or [],
        })
    issuers.sort(key=lambda x: (x["status"], x["symbol"]))
    counts = Counter(x["status"] for x in issuers)
    return {
        "version": "nour-sector-evidence-v1",
        "analysis_date": report.get("analysis_date"),
        "universe": len(issuers),
        "families": dict(sorted(Counter(x["family"] or "Métier inconnu" for x in issuers).items())),
        "review_states": dict(sorted(counts.items())),
        "curated": sum(x["classification"] == "curated" for x in issuers),
        "selected_pages_reviewed_issuers": sum(x["selected_page_evidence_count"] > 0 for x in issuers),
        "violations": violations,
        "issuers": issuers,
        "documents_certified": False,
        "method": "Inventaire de contrôles documentaires par métier; les KPI demandés ne sont pas des valeurs observées.",
        "limitations": "Un PDF référencé ou une page sélectionnée vérifiée ne certifie pas le rapport entier ni le périmètre de consolidation.",
    }
