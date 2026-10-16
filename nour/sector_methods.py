"""Sector-specific analytical checklist. Read-only metadata; never changes Nour scores.

Every ratio remains subject to primary evidence, compatible accounting basis,
period and units. A missing business KPI must not be inferred from price data.
"""

from .peer_groups import group_for

FAMILIES = {
    "Banque": {
        "symbols": ("ATW", "BCP", "BOA", "BMC", "CIH", "CDM", "CFGB"),
        "metrics": ("PNB", "RNPG", "coût du risque", "créances en souffrance", "solvabilité", "ROE"),
        "exclude": ("CA industriel", "dette nette/EBITDA industriel"),
        "sources": ("rapports consolidés", "communications BAM", "AMMC"),
    },
    "Assurance": {
        "symbols": ("WAF", "ATL", "SAF"),
        "metrics": ("primes", "sinistralité", "résultat technique", "solvabilité", "placements"),
        "exclude": ("EBITDA industriel", "comparaison avec courtiers"),
        "sources": ("états prudentiels", "rapports de gestion", "ACAPS", "AMMC"),
    },
    "Immobilier - promotion": {
        "symbols": ("ADI", "ADH", "RDS"),
        "metrics": ("préventes", "livraisons", "encaissements", "marge", "BFR", "dette nette"),
        "exclude": ("revenus locatifs comme mesure principale", "valorisation sur préventes non encaissées"),
        "sources": ("rapports annuels", "communiqués d'activité", "AMMC"),
    },
    "BTP et ingénierie": {
        "symbols": ("TGCC", "SGTM", "JET"),
        "metrics": ("carnet de commandes", "prise de commandes", "marge chantier", "BFR", "trésorerie", "capex"),
        "exclude": ("préventes immobilières comme CA", "carnet de commandes comme bénéfice acquis"),
        "sources": ("rapports de gestion", "résultats consolidés", "AMMC"),
    },
    "Tourisme et hôtellerie": {
        "symbols": ("RIS",),
        "metrics": ("taux d'occupation", "ADR", "RevPAR", "marge opérationnelle", "dette", "saisonnalité"),
        "exclude": ("carnet de commandes BTP", "PNB bancaire"),
        "sources": ("rapports de gestion", "résultats", "observatoires touristiques"),
    },
    "Santé - hôpitaux": {
        "symbols": ("AKD",),
        "metrics": ("capacité lits", "taux d'occupation si publié", "activité par spécialité", "marge opérationnelle", "capex", "dette"),
        "exclude": ("rotation des stocks comme indicateur principal", "PNB bancaire"),
        "sources": ("rapports de l'opérateur", "résultats consolidés", "AMMC"),
    },
    "Santé - industrie pharmaceutique": {
        "symbols": ("SOT", "PPM"),
        "metrics": ("croissance organique", "marge brute", "mix produits", "stocks", "BFR", "capex"),
        "exclude": ("taux d'occupation hôtelier", "PNB bancaire"),
        "sources": ("rapports émetteurs", "résultats", "AMMC"),
    },
    "Santé - distribution et équipements": {
        "symbols": ("VCNE",),
        "metrics": ("chiffre d'affaires par segment", "marge de distribution", "stocks", "BFR", "capex", "créances"),
        "exclude": ("taux d'occupation hospitalier comme indicateur direct du distributeur", "PNB bancaire"),
        "sources": ("rapports émetteurs", "résultats", "AMMC"),
    },
    "Agroalimentaire et boissons": {
        "symbols": ("LES", "MUT", "OUL", "UNI", "CAR", "CSR"),
        "metrics": ("volumes", "prix/mix", "coûts des intrants", "marge", "stocks", "BFR", "capex"),
        "exclude": ("PNB bancaire", "carnet de commandes BTP"),
        "sources": ("rapports émetteurs", "résultats", "AMMC"),
    },
    "Métallurgie et matériaux industriels": {
        "symbols": ("SNA",),
        "metrics": ("volumes", "prix moyens", "coûts de l'énergie", "marge", "BFR", "capex"),
        "exclude": ("production minière supposée", "PNB bancaire"),
        "sources": ("rapports émetteurs", "résultats", "AMMC"),
    },
    "Agriculture et intrants": {
        "symbols": ("CMGP",),
        "metrics": ("saisonnalité", "mix produits", "marge brute", "stocks", "BFR", "créances clients"),
        "exclude": ("carnet de commandes BTP", "PNB bancaire"),
        "sources": ("rapports émetteurs", "statistiques agricoles", "AMMC"),
    },
    "Télécommunications": {
        "symbols": ("IAM",),
        "metrics": ("ARPU", "abonnés", "churn si publié", "capex réseau", "marge", "cash-flow"),
        "exclude": ("PNB bancaire", "RevPAR hôtelier"),
        "sources": ("rapports opérateur", "ANRT", "AMMC"),
    },
    "Matériaux de construction - ciment": {
        "symbols": ("LHM", "CIM"),
        "metrics": ("volumes ciment", "prix moyens si publiés", "énergie", "marge", "capex"),
        "exclude": ("carnet de commandes BTP comme chiffre d’affaires du cimentier",),
        "sources": ("rapports émetteurs", "statistiques sectorielles", "AMMC"),
    },
    "Distribution de carburants et gaz": {
        "symbols": ("TMA", "GAZ"),
        "metrics": ("volumes distribués", "marge unitaire si publiée", "stocks", "BFR", "capex"),
        "exclude": ("production pétrolière amont supposée", "PNB bancaire"),
        "sources": ("rapports émetteurs", "AMMC"),
    },
    "Production électrique": {
        "symbols": ("TQA",),
        "metrics": ("disponibilité", "production MWh", "contrats d’achat", "coût combustible", "dette", "capex"),
        "exclude": ("marge commerciale d’une station-service",),
        "sources": ("rapports émetteurs", "AMMC"),
    },
    "Grande distribution": {
        "symbols": ("LBV",),
        "metrics": ("ventes à périmètre comparable", "marge", "rotation stocks", "BFR", "capex"),
        "exclude": ("taux d’occupation hôtelier", "PNB bancaire"),
        "sources": ("rapports émetteurs", "AMMC"),
    },
    "Transport routier": {
        "symbols": ("CTM",),
        "metrics": ("voyageurs", "taux de remplissage si publié", "prix moyen", "coût carburant", "capex"),
        "exclude": ("EVP portuaires", "RevPAR hôtelier"),
        "sources": ("rapports émetteurs", "AMMC"),
    },
    "Ports et logistique": {
        "symbols": ("MSA",),
        "metrics": ("tonnage", "EVP", "capacité", "utilisation", "tarifs", "capex", "cash-flow"),
        "exclude": ("RevPAR hôtelier", "PNB bancaire"),
        "sources": ("rapports d'exploitation", "résultats", "AMMC"),
    },
    "Mines": {
        "symbols": ("SMI", "MNG", "CMT"),
        "metrics": ("production", "teneur", "coût unitaire", "cours des métaux", "capex", "cash-flow"),
        "exclude": ("tonnage portuaire comme production minière", "PNB bancaire"),
        "sources": ("rapports miniers", "résultats", "AMMC"),
    },
    "Technologie et services": {
        "symbols": ("T2S", "HPS", "M2M", "S2M"),
        "metrics": ("revenus récurrents si publiés", "marge", "concentration clients", "BFR", "cash-flow"),
        "exclude": ("ARR supposé sans publication", "multiple SaaS pour activités non SaaS"),
        "sources": ("rapports émetteurs", "résultats", "AMMC"),
    },
}


def guidance(symbol, record=None):
    """Return a descriptive checklist, not observed financial data or advice."""
    if not isinstance(symbol, str):
        raise TypeError("Symbol must be text")
    record = record or {}
    for family, details in FAMILIES.items():
        if symbol in details["symbols"]:
            return {
                "family": family,
                "coverage": "curated",
                "metrics_to_verify": list(details["metrics"]),
                "invalid_shortcuts": list(details["exclude"]),
                "source_priorities": list(details["sources"]),
                "note": "Indicateurs à rechercher, non valeurs mesurées. Exiger pages, dates, périmètres et unités avant calcul.",
            }
    group, kind = group_for(symbol, record)
    return {
        "family": group or "Métier non qualifié",
        "coverage": "broad_only" if kind == "broad_sector" else "partial",
        "metrics_to_verify": [],
        "invalid_shortcuts": [],
        "source_priorities": ["rapports de l'émetteur", "AMMC"],
        "note": "Méthode sectorielle non validée : pas de comparaison métier automatique.",
    }
