"""Conservative Moroccan economic source registry, separate from issuer accounting facts.

Registry links and macro series are discovery/context only, never score inputs.
"""
from __future__ import annotations

from collections import Counter
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

CATALOG = Path(__file__).resolve().parents[1] / "data" / "economic_source_catalog.json"
ROLES = frozenset(("issuer_document", "market_prices", "security_reference",
                   "prudential_context", "sector_context", "macro_context", "policy_context"))


def load_catalog(path=CATALOG):
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    if (catalog.get("schema_version") != 1
            or catalog.get("usable_for_score") is not False
            or catalog.get("usable_to_certify_issuer_financial_facts") is not False
            or not isinstance(catalog.get("institutions"), list)):
        raise ValueError("invalid economic source catalog contract")
    seen = set()
    for entry in catalog["institutions"]:
        if not isinstance(entry, dict):
            raise ValueError("invalid source entry")
        key = entry.get("id")
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError("duplicate or missing source id")
        seen.add(key)
        if (entry.get("role") not in ROLES
                or not isinstance(entry.get("name"), str) or not entry["name"]
                or not isinstance(entry.get("sectors"), list) or not entry["sectors"]
                or entry.get("automatic_import") is not False
                or entry.get("rights_status") != "not_assessed"):
            raise ValueError("source missing provenance or explicit import restriction")
        if entry.get("issuer_accounting_fact_authority") is not (entry["role"] == "issuer_document"):
            raise ValueError("context source falsely authorized for accounting facts")
        url = entry.get("url")
        if url is not None:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.port not in (None, 443)
                    or "\\" in url):
                raise ValueError("unsafe economic source URL")
    return catalog


def catalog_summary(catalog):
    institutions = catalog["institutions"]
    return {
        "schema_version": 1,
        "institution_count": len(institutions),
        "roles": dict(sorted(Counter(x["role"] for x in institutions).items())),
        "auto_import_enabled": False,
        "usable_for_score": False,
        "usable_to_certify_issuer_financial_facts": False,
    }


def catalog_page(catalog):
    """Static human-readable view with escaped registry fields."""
    rows = []
    for source in sorted(catalog["institutions"], key=lambda x: (x["role"], x["name"])):
        url = source.get("url")
        link = (f'<a href="{escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">Site officiel ↗</a>'
                if url else "Adresse à vérifier")
        rows.append(
            f'<tr><td>{escape(source["name"])}</td>'
            f'<td>{escape(source["role"])}</td>'
            f'<td>{escape(", ".join(source["sectors"]))}</td>'
            f'<td>{escape(source["scope"])}</td>'
            f'<td>{escape(source["verification_status"])} · {link}</td></tr>')
    return (
        '<main><div class="hero"><span class="eyebrow">Sources économiques · inventaire prudent</span>'
        '<h1>Sources officielles marocaines</h1>'
        '<p>Registre documentaire et contexte sectoriel. Aucune donnée de ce registre '
        'ne modifie les scores ou ne certifie les comptes des sociétés. '
        'Les droits de réutilisation et les liens doivent être vérifiés avant automatisation.</p></div>'
        '<section class="panel"><h2>Registre des institutions</h2>'
        '<div style="overflow-x:auto"><table><thead><tr>'
        '<th>Institution</th><th>Usage</th><th>Métiers</th><th>À rechercher</th>'
        '<th>État / accès</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table></div></section></main>'
    )
