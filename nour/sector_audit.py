"""Independent sector-by-sector evidence inventory, not a source of new ratios.

Runs over the already-computed Nour report. Never overwrites a fundamental,
a market price or a canonical score. No external fetch and no PDF certification.
"""
from collections import Counter
from datetime import date
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
    "Finance - crédit-bail": (("produit_net_bancaire",), ("resultat_net_part_groupe", "resultat_net_social")),
    "Finance - crédit à la consommation": (("produit_net_bancaire",), ("resultat_net_part_groupe", "resultat_net_social")),
    "Finance - services de paiement": (("chiffre_affaires",),),
    "Assurance - courtage": (("chiffre_affaires",),),
    "Immobilier - foncières": (("chiffre_affaires",),),
    "Holdings et participations": (("resultat_net_part_groupe", "resultat_net_social"),),
    "Assurance": (("resultat_net_part_groupe", "resultat_net_social"),),
    "Immobilier - promotion": (("chiffre_affaires",), ("resultat_net_part_groupe", "resultat_net_social")),
    "BTP et ingénierie": (("chiffre_affaires",), ("resultat_net_part_groupe", "resultat_net_social")),
    "Tourisme et hôtellerie": (("chiffre_affaires",),),
    "Santé - hôpitaux": (("chiffre_affaires",),),
    "Santé - industrie pharmaceutique": (("chiffre_affaires",),),
    "Santé - distribution et équipements": (("chiffre_affaires",),),
    "Agroalimentaire et boissons": (("chiffre_affaires",),),
    "Métallurgie et matériaux industriels": (("chiffre_affaires",),),
    "Agriculture et intrants": (("chiffre_affaires",),),
    "Ports et logistique": (("chiffre_affaires",),),
    "Mines": (("chiffre_affaires",),),
    "Technologie et services": (("chiffre_affaires",),),
    "Distribution automobile": (("chiffre_affaires",),),
    "Distribution informatique": (("chiffre_affaires",),),
    "Services informatiques et logiciels": (("chiffre_affaires",),),
    "Industrie - papier": (("chiffre_affaires",),),
    "Industrie - chimie et gaz": (("chiffre_affaires",),),
    "Industrie - équipements et métallurgie": (("chiffre_affaires",),),
    "Distribution industrielle": (("chiffre_affaires",),),
    "Peintures et revêtements": (("chiffre_affaires",),),
}
# These are institution-specific accounting incompatibilities, not
# cross-sector rankings. Other financial services need individual review.
NON_INDUSTRIAL_DEBT_FAMILIES = frozenset(("Banque", "Assurance",
                                          "Finance - crédit-bail", "Finance - crédit à la consommation"))


def _primary_checked(fact):
    if not isinstance(fact, dict):
        return False
    try:
        date.fromisoformat(fact.get('period_end'))
    except (TypeError, ValueError):
        return False
    return (fact.get('currency') == 'MAD'
            and fact.get('unit') in ('MMAD', 'actions', 'MAD', 'DH')
            and fact.get("validation_status") in CHECKED
            and isinstance(fact.get("page"), int) and not isinstance(fact["page"], bool)
            and fact["page"] > 0
            and isinstance(fact.get("document_url"), str)
            and fact["document_url"].startswith("https://")
            and isinstance(fact.get("document_hash"), str)
            and HASH.fullmatch(fact["document_hash"]) is not None
            and bool(fact.get("accounting_basis")))


ACTION_RULES = {
    "debt_arithmetic_mismatch": (
        "P1", "Rapprocher le périmètre de dette nette publié avec les postes du bilan et les notes annexes ; ne pas forcer le rapprochement."
    ),
    "group_earnings_missing_total_not_substituted": (
        "P1", "Rechercher le résultat net part du groupe dans les états consolidés ; ne pas utiliser le résultat consolidé total."
    ),
    "currency_conversion_not_documented": (
        "P1", "Identifier la devise, le taux et la date de conversion publiés ; conserver les ratios suspendus."
    ),
    "invalid_numeric_fact": (
        "P1", "Relever la valeur, l'unité et la colonne de période dans le document primaire."
    ),
    "fact_unit_mismatch": (
        "P1", "Vérifier les unités imprimées, puis documenter toute conversion."
    ),
    "fact_period_mismatch": (
        "P1", "Vérifier la colonne de l'exercice et le périmètre comptable."
    ),
    "calculation_basis_mismatch": (
        "P1", "Reconstituer les deux postes sur un périmètre comptable homogène."
    ),
    "earnings_equity_scope_mismatch": (
        "P1", "Aligner résultat et capitaux propres : social/social ou groupe/groupe."
    ),
    "share_denominator_invalid": (
        "P1", "Rapprocher le nombre de titres à la date de clôture et la moyenne pondérée du BPA."
    ),
    "nonpositive_denominator": (
        "P1", "Vérifier le dénominateur et expliquer pourquoi le ratio est non significatif."
    ),
    "nonpositive_earnings_per_not_meaningful": (
        "P2", "Conserver le résultat négatif et le PER indisponible ; aucune correction à inventer."
    ),
}


def _review_actions(symbol, audit):
    """Actionable checks based exclusively on the already published audit."""
    actions = []
    for check in audit.get('checks') or []:
        code = check.get('code')
        if check.get('status') != 'blocked' or code not in ACTION_RULES:
            continue
        priority, instruction = ACTION_RULES[code]
        action = {
            'symbol': symbol,
            'priority': priority,
            'code': code,
            'instruction': instruction,
            'fields': check.get('fields') or [],
            'blocked_metrics': check.get('blocked_metrics') or [],
        }
        if code == 'debt_arithmetic_mismatch':
            debt = audit.get('debt_comparison') or {}
            if debt.get('status') == 'unresolved':
                action['debt_comparison_mmad'] = {
                    key: debt.get(key) for key in (
                        'calculated_mmad', 'reported_mmad', 'difference_mmad',
                        'tolerance_mmad')
                }
        actions.append(action)
    return actions


def audit_sector_report(report):
    """Return an auditable issuer queue. 'No violations' is not certification."""
    issuers, violations, review_queue = [], [], []
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
        unverified = ["/".join(alternatives) for alternatives in required
                      if any(key in evidence for key in alternatives)
                      and not any(_primary_checked(evidence.get(key)) for key in alternatives)]
        audit = f.get("financial_audit") or {}
        audit_status = audit.get("status", "unavailable")
        actions = _review_actions(symbol, audit)
        for action in actions:
            action["document_url"] = f.get("document_url")
            action["annual_exercise"] = f.get("exercise")
            action["accounting_basis"] = f.get("accounting_basis")
            action["source_pages_to_check"] = [
                {"field": key, "page_hint": evidence[key].get("page"),
                 "status": evidence[key].get("validation_status")}
                for key in action.get("fields", [])
                if isinstance(evidence.get(key), dict)
                and isinstance(evidence[key].get("page"), int)
                and not isinstance(evidence[key]["page"], bool)
            ]
        review_queue.extend(actions)
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
        elif missing or unverified or audit_status != "checked":
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
            "unverified_annual_fact_groups": unverified,
            "business_kpis_to_collect": method["metrics_to_verify"],
            "accounting_exclusions": method["invalid_shortcuts"],
            "blocked_metrics": audit.get("blocked_metrics") or [],
            "review_actions": actions,
        })
    issuers.sort(key=lambda x: (x["status"], x["symbol"]))
    counts = Counter(x["status"] for x in issuers)
    review_queue.sort(key=lambda x: (x["priority"], x["symbol"], x["code"]))
    return {
        "version": "nour-sector-evidence-v2",
        "analysis_date": report.get("analysis_date"),
        "universe": len(issuers),
        "families": dict(sorted(Counter(x["family"] or "Métier inconnu" for x in issuers).items())),
        "review_states": dict(sorted(counts.items())),
        "curated": sum(x["classification"] == "curated" for x in issuers),
        "selected_pages_reviewed_issuers": sum(x["selected_page_evidence_count"] > 0 for x in issuers),
        "violations": violations,
        "review_queue": review_queue,
        "blocking_issuers": sum(bool(x["blocked_metrics"]) for x in issuers),
        "blocking_actions": len(review_queue),
        "issuers": issuers,
        "documents_certified": False,
        "method": "Inventaire de contrôles documentaires par métier; les KPI demandés ne sont pas des valeurs observées.",
        "limitations": "Un PDF référencé ou une page sélectionnée vérifiée ne certifie pas le rapport entier ni le périmètre de consolidation.",
    }
