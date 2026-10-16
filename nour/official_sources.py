"""Official document discovery, isolated from financial facts and score inputs.

An indexed PDF is a candidate, never a read/validated financial statement.
Only an explicit issuer registry can authorize an origin; redirects obey it too.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .news import AMMC_INDEX, _words

MAX_HTML = 3_000_000
MAX_PDF = 32_000_000


def safe_url(url, origins):
    """HTTPS exact-origin allowlist, no credentials, fragments or unusual ports."""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
                parsed.password or parsed.port not in (None, 443) or '\\' in url):
            return None
        origin = 'https://' + parsed.hostname.lower()
        if origin not in origins:
            return None
        return urlunsplit(('https', parsed.hostname.lower(), parsed.path or '/', parsed.query, ''))
    except (ValueError, TypeError):
        return None


class _Redirect(HTTPRedirectHandler):
    def __init__(self, origins):
        self.origins = origins

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        clean = safe_url(urljoin(req.full_url, newurl), self.origins)
        if not clean:
            raise ValueError('redirect outside official allowlist')
        return super().redirect_request(req, fp, code, msg, headers, clean)


def fetch(url, origins, *, timeout=15, max_bytes=MAX_HTML):
    clean = safe_url(url, origins)
    if not clean:
        raise ValueError('URL outside official allowlist')
    opener = build_opener(_Redirect(origins))
    with opener.open(Request(clean, headers={'User-Agent': 'BVCAnalyzerNour/official-discovery-1'}),
                     timeout=timeout) as response:
        final = safe_url(response.geturl(), origins)
        if not final:
            raise ValueError('response outside official allowlist')
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError('document exceeds size limit')
        return body, final, response.headers.get('Content-Type', '')


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs = dict(attrs)
            self.active = [attrs.get('href', ''), attrs.get('title', '')]

    def handle_data(self, data):
        if self.active is not None:
            self.active[1] += ' ' + data

    def handle_endtag(self, tag):
        if tag == 'a' and self.active is not None:
            self.links.append(self.active)
            self.active = None


def document_links(body, base_url, origins):
    parser = _Links()
    parser.feed(body.decode('utf-8', 'replace'))
    found = {}
    for href, title in parser.links:
        url = safe_url(urljoin(base_url, href), origins)
        if url and urlsplit(url).path.lower().endswith('.pdf'):
            found.setdefault(url, {'url': url, 'title': ' '.join(title.split())[:220]})
    return list(found.values())


def validate_registry(registry):
    if not isinstance(registry, dict) or registry.get('schema_version') != 1 or not isinstance(registry.get('issuers'), dict):
        raise ValueError('unsupported official-source registry')
    for symbol, issuer in registry['issuers'].items():
        if (not isinstance(issuer, dict) or issuer.get('record_id') != symbol or
                not isinstance(issuer.get('name'), str) or not issuer['name']):
            raise ValueError('issuer identity missing: ' + symbol)
        origins = issuer.get('allowed_origins', [])
        if (not isinstance(origins, list) or not origins or
                any(not isinstance(o, str) or safe_url(o, origins) != o + '/' for o in origins)):
            raise ValueError('invalid origin: ' + symbol)
        for field in ('pages', 'aliases'):
            if not isinstance(issuer.get(field, []), list) or any(
                    not isinstance(v, str) for v in issuer.get(field, [])):
                raise ValueError('invalid issuer ' + field)
        if not isinstance(issuer.get('reference_documents', []), list):
            raise ValueError('invalid issuer references')
        for page in issuer.get('pages', []):
            if not safe_url(page, origins):
                raise ValueError('unapproved issuer page: ' + symbol)
        for ref in issuer.get('reference_documents', []):
            if not isinstance(ref, dict) or not safe_url(ref.get('url'), origins):
                raise ValueError('unapproved reference: ' + symbol)
    return registry


def validate_state(state):
    """Reject malformed cache before mutation; never replace a corrupt last-good file."""
    if (not isinstance(state, dict) or state.get('schema_version') != 1 or
            not isinstance(state.get('documents'), list) or not isinstance(state.get('sources'), dict)):
        raise ValueError('invalid official candidate state structure')
    seen = set()
    for doc in state['documents']:
        if (not isinstance(doc, dict) or not isinstance(doc.get('id'), str) or not doc['id'] or
                doc['id'] in seen or not isinstance(doc.get('url'), str) or
                not isinstance(doc.get('tickers'), list) or
                any(not isinstance(t, str) for t in doc['tickers'])):
            raise ValueError('invalid official candidate document')
        seen.add(doc['id'])
        for field in ('listed_by', 'identical_content_urls'):
            if field in doc and (not isinstance(doc[field], list) or
                                 any(not isinstance(v, str) for v in doc[field])):
                raise ValueError('invalid candidate ' + field)
        for field in ('match_evidence', 'content_history'):
            if field in doc and (not isinstance(doc[field], list) or
                                 any(not isinstance(v, dict) for v in doc[field])):
                raise ValueError('invalid candidate ' + field)
        if 'sha256' in doc and (not isinstance(doc['sha256'], str) or len(doc['sha256']) != 64 or
                               any(c not in '0123456789abcdef' for c in doc['sha256'])):
            raise ValueError('invalid candidate content hash')
        if 'sha256' in doc and (not isinstance(doc.get('fetched_at'), str) or
                                not isinstance(doc.get('byte_length'), int)):
            raise ValueError('invalid candidate content metadata')
    if any(not isinstance(url, str) or not isinstance(source, dict)
           for url, source in state['sources'].items()):
        raise ValueError('invalid official source state')
    return state


def match_candidates(link, issuers, targets, kind, page):
    """Association evidence only; issuer-page ownership of every PDF is unverified."""
    evidence = []
    title_words = ' ' + _words(link['title']) + ' '
    for symbol in sorted(targets):
        issuer = issuers[symbol]
        if kind == 'issuer':
            evidence.append(dict(ticker=symbol, method='issuer_page', source=page,
                                 matched_value=page))
            continue
        aliases = [issuer['name'], *issuer.get('aliases', [])]
        matches = [a for a in aliases if len(_words(a)) >= 4 and
                   ' ' + _words(a) + ' ' in title_words]
        pinned = any(ref['url'] == link['url'] for ref in issuer.get('reference_documents', []))
        if matches:
            evidence.append(dict(ticker=symbol, method='official_index_name', source=page,
                                 matched_value=matches[0]))
        elif pinned:
            evidence.append(dict(ticker=symbol, method='pinned_reference_url', source=page,
                                 matched_value=link['url']))
    return evidence


def collect(registry, previous=None, *, fetcher=fetch, now=None, fetch_documents=False,
            max_documents=10, cache_dir=None, symbols=None):
    """Refresh candidates. Source failures retain candidates and last-success time.

    Only five seeded investor pages + one shared AMMC index are requested by
    default, never the 80 issuers' individual reference PDFs. PDF fetch is opt-in.
    """
    validate_registry(registry)
    stamp = now or datetime.now(timezone.utc).isoformat()
    initial = {'schema_version': 1, 'documents': [], 'sources': {}} if previous is None else previous
    validate_state(initial)
    state = deepcopy(initial)
    state.update(checked_at=stamp, role='candidate_links_only', usable_for_score=False)
    sources = state.setdefault('sources', {})
    docs = {d['id']: d for d in state.get('documents', [])}
    selected = set(symbols or registry['issuers'])
    unknown = selected - set(registry['issuers'])
    if unknown:
        raise ValueError('unknown symbols: ' + ', '.join(sorted(unknown)))
    issuers = {s: r for s, r in registry['issuers'].items() if s in selected}
    tasks = {AMMC_INDEX: (set(issuers), ['https://www.ammc.ma', 'https://ammc.ma'], 'AMMC')}
    for symbol, issuer in issuers.items():
        for page in issuer.get('pages', []):
            tasks[page] = ({symbol}, issuer['allowed_origins'], 'issuer')
    pdf_budget = max(0, max_documents)
    downloaded = {}
    for page, (targets, origins, kind) in tasks.items():
        entry = deepcopy(sources.get(page, {}))
        entry.update(checked_at=stamp, tickers=sorted(targets))
        try:
            body, final, content_type = fetcher(page, origins, max_bytes=MAX_HTML)
            if not safe_url(final, origins) or 'pdf' in content_type.lower():
                raise ValueError('unexpected index response')
            page_hash = hashlib.sha256(body).hexdigest()
            new_count = 0
            links = document_links(body, final, origins)
            for link in links:
                evidence = match_candidates(link, issuers, targets, kind, page)
                tickers = sorted({e['ticker'] for e in evidence})
                if not tickers:
                    continue
                key = hashlib.sha256(link['url'].encode()).hexdigest()
                if key not in docs:
                    new_count += 1
                doc = docs.setdefault(key, dict(id=key, **link, first_seen=stamp,
                    status='indexed_not_read', usable_for_score=False, tickers=[]))
                prior_evidence = [e for e in doc.get('match_evidence', []) if e.get('source') != page]
                doc['match_evidence'] = prior_evidence + evidence
                doc['tickers'] = sorted({e['ticker'] for e in doc['match_evidence']})
                doc['last_seen'] = stamp
                doc['association_status'] = 'candidate_only_unverified'
                doc['pdf_issuer_ownership_validated'] = False
                doc['listed_by'] = sorted(set(doc.get('listed_by', [])) | {page})
                if fetch_documents and pdf_budget:
                    pdf_budget -= 1
                    doc['last_fetch_attempt'] = stamp
                    try:
                        data, pdf_final, _ = fetcher(link['url'], origins, max_bytes=MAX_PDF)
                        if not safe_url(pdf_final, origins) or not data.startswith(b'%PDF-'):
                            raise ValueError('not a PDF')
                        digest = hashlib.sha256(data).hexdigest()
                        if doc.get('sha256') and doc['sha256'] != digest:
                            doc.setdefault('content_history', []).append({
                                'sha256': doc['sha256'], 'fetched_at': doc['fetched_at'],
                                'byte_length': doc['byte_length'], 'replaced_at': stamp})
                        doc['fetch_status'] = 'success'
                        doc.update(sha256=digest, fetched_at=stamp, byte_length=len(data),
                                   status='downloaded_not_read')
                        doc.pop('fetch_error', None)
                        downloaded[digest] = data
                    except (OSError, ValueError) as exc:
                        doc['fetch_error'] = str(exc)[:180]
                        doc['fetch_status'] = 'error'
            entry.update(status='success' if new_count or page_hash != entry.get('sha256') else 'no_new',
                         last_success_at=stamp, sha256=page_hash, indexed_links=len(links),
                         new_candidates=new_count,
                         discovery_status='pdf_links_found' if links else 'no_pdf_links_visible')
            entry.pop('error', None)
        except (OSError, ValueError) as exc:
            entry.update(status='error', error=str(exc)[:180])
        sources[page] = entry
    # Mirror grouping uses bytes only; same filename/title never implies identity.
    groups = {}
    for doc in docs.values():
        if doc.get('sha256'):
            groups.setdefault(doc['sha256'], []).append(doc)
    for group in groups.values():
        urls = sorted(d['url'] for d in group)
        for doc in group:
            doc['identical_content_urls'] = urls
    if cache_dir is not None:
        folder = Path(cache_dir)
        folder.mkdir(parents=True, exist_ok=True)
        for digest, data in downloaded.items():
            target = folder / (digest + '.pdf')
            if not target.exists():
                target.write_bytes(data)
    state['documents'] = sorted(docs.values(), key=lambda d: d['id'])
    statuses = [sources[p]['status'] for p in tasks]
    state['status'] = ('error' if all(s == 'error' for s in statuses) else
                       'partial' if 'error' in statuses else 'ok')
    return state
