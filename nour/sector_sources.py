"""Bounded, read-only official sector publication discovery.

This module discovers links and records provenance. It never parses a number
into financial facts, quotes, issuer ratios, or the canonical score.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from html import escape
import unicodedata
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .official_sources import fetch, safe_url

MAX_HTML_BYTES = 2_000_000
MAX_LINKS_PER_SOURCE = 35
EXTENSIONS = (".pdf", ".xls", ".xlsx", ".csv")


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            self.active = [attrs.get("href", ""), attrs.get("title", "")]

    def handle_data(self, data):
        if self.active is not None:
            self.active[1] += " " + data

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            self.items.append(self.active)
            self.active = None


def validate_config(config):
    if (not isinstance(config, dict) or config.get("schema_version") != 1
            or config.get("usable_for_score") is not False
            or config.get("usable_for_issuer_ratios") is not False
            or not isinstance(config.get("sources"), list)):
        raise ValueError("invalid sector source watch contract")
    ids = set()
    for source in config["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            raise ValueError("invalid sector source")
        if source["id"] in ids:
            raise ValueError("duplicate sector source")
        ids.add(source["id"])
        origins = source.get("origins")
        if (not isinstance(origins, list) or not origins
                or not all(isinstance(o, str) and safe_url(o, origins) == o + "/" for o in origins)
                or not safe_url(source.get("url"), origins)
                or not isinstance(source.get("keywords"), list)
                or not source["keywords"]
                or not all(isinstance(k, str) and len(k) >= 3 for k in source["keywords"])
                or not isinstance(source.get("symbols"), list)):
            raise ValueError("invalid sector source allowlist")
    return config


def validate_state(state):
    if (not isinstance(state, dict) or state.get("schema_version") != 1
            or state.get("usable_for_score") is not False
            or state.get("usable_for_issuer_ratios") is not False
            or not isinstance(state.get("sources"), dict)):
        raise ValueError("invalid sector source cache")
    return state


def extract_links(body, base_url, origins, keywords):
    parser = _Anchors()
    parser.feed(body.decode("utf-8", "replace"))
    links = {}
    for href, title in parser.items:
        url = safe_url(urljoin(base_url, href), origins)
        if not url:
            continue
        label = " ".join(title.split())[:220]
        path = urlsplit(url).path.lower()
        document = path.endswith(EXTENSIONS)
        # Official sites often use English PDF filenames and French anchor labels.
        # A generic brochure, tariff or commemorative PDF is not a sector KPI.
        def fold(value):
            return "".join(ch for ch in unicodedata.normalize("NFKD", value.casefold())
                           if not unicodedata.combining(ch))
        haystack = fold(label + " " + path)
        if not any(fold(k) in haystack for k in keywords):
            continue
        if url == base_url:
            continue
        links[url] = {"url": url, "title": label, "type": "document_candidate" if document else "related_page"}
        if len(links) >= MAX_LINKS_PER_SOURCE:
            break
    return list(links.values())


def collect(config, previous=None, *, fetcher=fetch, now=None):
    validate_config(config)
    stamp = now or datetime.now(timezone.utc).isoformat()
    state = deepcopy(previous) if previous is not None else {
        "schema_version": 1, "usable_for_score": False,
        "usable_for_issuer_ratios": False, "sources": {}}
    validate_state(state)
    state["checked_at"] = stamp
    state["role"] = "publication_metadata_only_not_a_financial_statement"
    for source in config["sources"]:
        source_id = source["id"]
        entry = deepcopy(state["sources"].get(source_id, {}))
        entry["id"] = source_id
        entry["page_url"] = source["url"]
        entry["related_symbols"] = source["symbols"]
        entry["checked_at"] = stamp
        try:
            body, final, content_type = fetcher(source["url"], source["origins"],
                                               timeout=12, max_bytes=MAX_HTML_BYTES)
            if not safe_url(final, source["origins"]) or "pdf" in content_type.lower():
                raise ValueError("unexpected HTML index response")
            if not isinstance(body, bytes):
                raise ValueError("invalid HTML payload")
            links = extract_links(body, final, source["origins"], source["keywords"])
            previous_links = {x["url"]: x for x in entry.get("links", [])}
            for link in links:
                old = previous_links.get(link["url"], {})
                link["first_seen_at"] = old.get("first_seen_at", stamp)
                link["last_seen_at"] = stamp
            entry.update(status="success", page_url=final,
                         last_success_at=stamp, page_sha256=hashlib.sha256(body).hexdigest(),
                         links=links, link_count=len(links),
                         discovery_status="links_found" if links else "no_matching_links",
                         usable_for_score=False, usable_for_issuer_ratios=False)
            entry.pop("error", None)
        except (OSError, ValueError, UnicodeError) as exc:
            # Never erase last good metadata or pretend that old links are fresh.
            entry.update(status="error", error=str(exc)[:180],
                         usable_for_score=False, usable_for_issuer_ratios=False)
        state["sources"][source_id] = entry
    state["status"] = ("success" if all(x["status"] == "success" for x in state["sources"].values())
                       else "partial" if any(x["status"] == "success" for x in state["sources"].values())
                       else "error")
    return state


def read_config(path):
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))


def monitor_html(state):
    """Human-readable last-success status; never displays collected links as verified numbers."""
    if not state:
        return '<section class="panel"><h2>Collecte sectorielle</h2><p>Première collecte non exécutée.</p></section>'
    rows = []
    for source_id, entry in sorted(state.get("sources", {}).items()):
        last = entry.get("last_success_at") or "jamais"
        checked = entry.get("checked_at") or "inconnu"
        status = entry.get("status") or "unknown"
        if status == "success" and not entry.get("link_count"):
            status = "accessible · aucun document repéré"
        elif status == "error":
            status = "échec · " + str(entry.get("error") or "source indisponible")[:110]
        links = []
        for item in entry.get("links", [])[:8]:
            url = item.get("url")
            if not isinstance(url, str) or urlsplit(url).scheme != "https":
                continue
            title = item.get("title") or item.get("type") or "Publication candidate"
            links.append('<li><a href="' + escape(url, quote=True)
                         + '" target="_blank" rel="noopener noreferrer">'
                         + escape(str(title)) + '</a></li>')
        docs = ('<ul>' + "".join(links) + '</ul>') if links else 'Aucun lien retenu'
        rows.append('<tr><td>' + escape(source_id) + '</td><td>'
                    + escape(status) + '</td><td>'
                    + escape(last) + '</td><td>' + escape(checked)
                    + '</td><td>' + docs + '</td></tr>')
    return ('<section class="panel"><h2>Collecte sectorielle automatique</h2>'
            '<p>Liens candidats issus des pages publiques. Une collecte réussie ne '
            'certifie aucun chiffre ni la fraîcheur des documents liés.</p>'
            '<div style="overflow-x:auto"><table><thead><tr>'
            '<th>Source</th><th>Dernier essai</th><th>Dernier succès</th>'
            '<th>Vérifié à</th><th>Publications repérées</th>'
            '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div></section>')
