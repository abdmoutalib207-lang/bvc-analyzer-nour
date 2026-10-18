"""Durable, compact incident memory; never ingest exception text or credentials."""
from copy import deepcopy
from datetime import datetime, timezone, date
from hashlib import sha256
from decimal import Decimal, InvalidOperation
import json
import math
import re
from urllib.parse import urlsplit, urlunsplit

_CODE = re.compile(r"^[a-zA-Z0-9_.:-]{1,96}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_HOSTS = ('cdgcapitalbourse.ma', 'wafabourse.com', 'casablanca-bourse.com',
                 'ammc.ma', 'github.com', 'raw.githubusercontent.com', 'github.io')
_MEASURES = {'o', 'h', 'l', 'c', 'v', 'shares', 'quantity', 'turnover_mad',
             'day_shares', 'day_turnover_mad', 'turnover', 'amount', 'lines',
             'turnover_mad_actual', 'day_turnover_mad_actual', 'expected_lines',
             'observed_lines', 'difference_mad', 'difference_shares',
             'candle_shares', 'candle_turnover_mad'}


def _timestamp(now):
    if now is None:
        return datetime.now(timezone.utc).isoformat()
    value = now.isoformat() if isinstance(now, datetime) else str(now)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Une date avec fuseau est requise pour le journal')
    return parsed.isoformat()


def _blank(memory):
    if memory and memory.get('schema_version') != 1:
        raise ValueError('Version de mémoire inconnue')
    result = deepcopy(memory) if memory else {'schema_version': 1, 'entries': {}, 'lessons': {}}
    if not isinstance(result.get('entries'), dict) or not isinstance(result.get('lessons'), dict):
        raise ValueError('Mémoire invalide')
    return result


def _code(value, fallback):
    return value if isinstance(value, str) and _CODE.fullmatch(value) else fallback


def _session(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        return None


def _evidence(items):
    """Only public source URLs (no query/auth) and content hashes are retained."""
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return []
    result = []
    for item in items[:24]:
        if isinstance(item, str):
            item = {'url': item}
        if not isinstance(item, dict):
            continue
        record = {}
        for key in ('sha256', 'raw_sha256', 'evidence_sha256'):
            value = item.get(key)
            if isinstance(value, str) and _HASH.fullmatch(value):
                record[key] = value
        try:
            url = urlsplit(item.get('url') or item.get('source_url') or '')
            host = (url.hostname or '').lower()
            if url.scheme == 'https' and not url.username and not url.password and any(
                    host == h or host.endswith('.' + h) for h in _PUBLIC_HOSTS):
                record['url'] = urlunsplit(('https', url.netloc, url.path, '', ''))
        except (ValueError, TypeError):
            pass
        if record and record not in result:
            result.append(record)
    return result[:8]


def _values(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, number in value.items():
        if key not in _MEASURES or isinstance(number, bool):
            continue
        if number is None:
            result[key] = None
        elif isinstance(number, (int, float)) and math.isfinite(number):
            result[key] = number
        elif isinstance(number, str) and len(number) < 80:
            try:
                if Decimal(number).is_finite():
                    result[key] = number
            except InvalidOperation:
                pass
    return result


def _identity(session, code, symbol, fields):
    payload = [session, code, symbol, sorted(set(fields))]
    return sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()[:24]


def _observe(result, event, session, timestamp, resolved=False, evidence=None, correction=False):
    fallback = ('volume_mismatch' if correction else 'guard_refusal_' + sha256(
        str(event.get('reason') or 'unknown').encode()).hexdigest()[:12])
    code = _code(event.get('code') or event.get('reason_code'), fallback)
    symbol = _code(event.get('symbol'), 'MARKET')
    raw_fields = event.get('fields') if isinstance(event.get('fields'), list) else []
    fields = sorted({_code(f, 'unknown') for f in raw_fields})
    identifier = _identity(session, code, symbol, fields)
    proof = _evidence(evidence if evidence is not None else event.get('evidence') or event.get('sources'))
    old = result['entries'].get(identifier)
    entry = old or dict(id=identifier, session=session, code=code, symbol=symbol,
                        fields=fields, first_seen=timestamp, occurrences=0, reopenings=0)
    if old and old.get('status') == 'resolved' and not resolved:
        entry['reopenings'] = entry.get('reopenings', 0) + 1
    entry.update(last_seen=timestamp, occurrences=entry['occurrences'] + (entry.get('last_seen') != timestamp),
                 status='resolved' if resolved else 'open',
                 severity=event.get('severity') if event.get('severity') in
                 ('info', 'warning', 'error', 'critical') else 'error')
    entry['summary'] = ('Écart de volume contrôlé ligne par ligne' if correction
                        else 'Condition de collecte non satisfaite ; code du garde-volume conservé')
    if not old:
        entry['before'] = _values(event.get('before') or event.get('retained'))
    entry['after'] = _values(event.get('after') or event.get('observed'))
    entry['evidence'] = _evidence((entry.get('evidence') or []) + proof)
    if resolved:
        entry['resolved_at'] = timestamp
        entry['resolution'] = {'code': 'corroborated_correction', 'evidence': proof,
                               'before': _values(event.get('before') or event.get('retained')),
                               'after': _values(event.get('after') or event.get('observed'))}
    result['entries'][identifier] = entry
    return identifier


def record_lesson(memory, lesson, now=None):
    """Record a curated lesson; caller supplies reviewed wording, never raw errors."""
    result, timestamp = _blank(memory), _timestamp(now)
    key = _code(lesson.get('id'), None)
    if not key:
        raise ValueError('Identifiant stable requis pour une leçon')
    previous = result['lessons'].get(key) or {}
    result['lessons'][key] = dict(id=key, first_seen=previous.get('first_seen', timestamp),
        last_seen=timestamp, occurrences=previous.get('occurrences', 0) + 1,
        title=str(lesson.get('title') or '')[:160],
        rule=str(lesson.get('rule') or '')[:600],
        evidence=_evidence((previous.get('evidence') or []) + _evidence(lesson.get('evidence'))))
    result['updated_at'] = timestamp
    return result


def update_error_memory(memory, audit, now=None):
    """Fold normalized guard incidents into permanent memory, without network errors.

    Refusals always remain open. Corrections require a positive audit and explicit
    public evidence to resolve an existing incident. Missing sources resolve none.
    """
    result, timestamp = _blank(memory), _timestamp(now)
    session = _session(audit.get('session'))
    if not session and audit.get('status') in ('matched', 'reconciled'):
        raise ValueError('Séance explicite requise pour une résolution')
    for event in audit.get('refusals') or []:
        if isinstance(event, dict):
            _observe(result, event, session, timestamp)
    for event in audit.get('proposed_corrections') or []:
        if isinstance(event, dict) and event not in (audit.get('corrections') or []):
            _observe(result, event, session, timestamp, correction=True)
    proof = _evidence(audit.get('providers'))
    positive = (audit.get('status') in ('matched', 'reconciled')
                and audit.get('publication_safe') is True
                and audit.get('internal_match') is True
                and audit.get('cross_source_verified') is True and bool(proof))
    for event in audit.get('corrections') or []:
        if isinstance(event, dict):
            event_proof = _evidence(event.get('evidence') or event.get('sources')) or proof
            in_scope = (event.get('symbol') in (audit.get('validated_symbols') or [])
                        and set(event.get('fields') or []) <= set(audit.get('validated_fields') or []))
            _observe(result, event, session, timestamp, resolved=positive and in_scope,
                     evidence=event_proof, correction=True)
    if positive:
        symbols = set(audit.get('validated_symbols') or [])
        fields = set(audit.get('validated_fields') or [])
        for entry in result['entries'].values():
            if (entry.get('session') == session and entry.get('status') == 'open'
                    and (entry.get('symbol') == 'MARKET' or entry.get('symbol') in symbols)
                    and set(entry.get('fields') or []) <= fields):
                entry.update(status='resolved', resolved_at=timestamp)
                entry['resolution'] = {'code': 'same_session_linewise_corroborated', 'evidence': proof}
    result['updated_at'] = timestamp
    result['last_audit'] = dict(session=session, status=_code(audit.get('status'), 'unknown'),
                               checked_at=timestamp)
    return result
