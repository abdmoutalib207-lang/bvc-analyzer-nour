"""Public Wafabourse cash-equity observation, independent of Nour/CDG.

The SELECT action, parameters and fields are those used by Wafabourse's
public market-tracking frontend (modules 77795 and 53664, observed 2026-10-18).
No login, private key, guessed endpoint, historical substitution or retry loop.
The transient frontend proxy token is never returned, logged or persisted.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import http.cookiejar
import json
import math
import re
import urllib.error
import urllib.request


ORIGIN = 'https://www.wafabourse.com'
SOURCE_URL = ORIGIN + '/fr/market-tracking/instruments-financiers'
ACTION = 'MARKET-LIST-SYMBOL'
MAX_BYTES = 2_000_000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError('public_source_redirect_refused')


def _result(observed_at):
    return dict(provider='Wafabourse', status='invalid', session=None,
                observed_at=observed_at, scope='cash_equities', source_url=SOURCE_URL,
                market_closed=False, rows=[], notices=[])


def _number(value, *, positive=False, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError('invalid_numeric_field')
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid_numeric_field') from exc
    if not number.is_finite() or number < 0 or (positive and number <= 0):
        raise ValueError('invalid_numeric_field')
    if integer and number != number.to_integral_value():
        raise ValueError('invalid_share_quantity')
    converted = int(number) if integer else float(number)
    if not integer and not math.isfinite(converted):
        raise ValueError('invalid_numeric_field')
    return converted


def parse_wafabourse(payload, *, observed_at=None, expected_session=None):
    """Validate the actual API envelope; never infer a session from download time.

    Only dated positive-amount transactions enter the reconciliation set. Empty
    frontend placeholders are accepted solely when date, amount, price and share
    quantity are all empty. A malformed positive observation invalidates the
    complete source rather than quietly changing its aggregate.
    """
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()
    result = _result(observed_at)
    try:
        observed_date = datetime.fromisoformat(observed_at.replace('Z', '+00:00')).date()
        if expected_session is not None:
            date.fromisoformat(expected_session)
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError('invalid_api_envelope')
        envelope = payload[0]
        if not isinstance(envelope, dict) or set(envelope) != {ACTION}:
            raise ValueError('invalid_api_action')
        action = envelope[ACTION]
        if not isinstance(action, dict) or action.get('Valid') is not True:
            raise ValueError('source_action_not_valid')
        source_rows = action.get('Data')
        if not isinstance(source_rows, list) or not source_rows or len(source_rows) > 500:
            raise ValueError('invalid_source_rows')
        rows, sessions, symbols, inactive = [], set(), set(), []
        closed = True
        for row in source_rows:
            if (not isinstance(row, dict) or isinstance(row.get('IdTypeValeur'), bool)
                    or row.get('IdTypeValeur') != 1):
                raise ValueError('unexpected_instrument_type')
            symbol = row.get('Symbol')
            if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z][A-Z0-9]{1,11}', symbol):
                raise ValueError('invalid_symbol')
            if symbol in symbols:
                raise ValueError('duplicate_symbol')
            symbols.add(symbol)
            closed = closed and row.get('Etat') == 'Market Close'
            amount, price = row.get('Volumes'), row.get('Cours')
            raw_date, quantity = row.get('DateDernierCours'), row.get('QteEchangee')
            if all(value in ('', None) for value in (amount, price, raw_date, quantity)):
                inactive.append(symbol)
                continue
            if not isinstance(raw_date, str) or not re.fullmatch(
                    r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', raw_date):
                raise ValueError('missing_or_invalid_transaction_date')
            session_date = datetime.strptime(raw_date, '%d/%m/%Y %H:%M:%S').date()
            if session_date.year == 1900:
                result['notices'].append(f'{symbol}: date de transaction {session_date:%d/%m/%Y} non exploitable ; aucune date de remplacement déduite.')
                raise ValueError('placeholder_transaction_session')
            if session_date.weekday() >= 5 or session_date > observed_date:
                raise ValueError('invalid_transaction_session')
            session = session_date.isoformat()
            sessions.add(session)
            amount = _number(amount, positive=True)
            price = _number(price, positive=True)
            # QteEchangee is the API's explicit share field. VTO, order-book
            # quantities and the PDF's repeated monetary Qté are never used.
            shares = None if quantity in ('', None) else _number(quantity, positive=True, integer=True)
            if shares is not None and Decimal(str(quantity)) == Decimal(str(row['Volumes'])):
                shares = None
                result['notices'].append(symbol + ': quantité identique au montant ; non utilisée.')
            rows.append(dict(symbol=symbol, session=session, price=price,
                             amount_mad=amount, shares=shares))
        if not rows or len(sessions) != 1:
            raise ValueError('mixed_or_empty_transaction_sessions')
        session = next(iter(sessions))
        if expected_session is not None and session != expected_session:
            raise ValueError('session_mismatch')
        if inactive:
            result['notices'].append(f'{len(inactive)} instruments sans transaction datée exclus du total.')
        if any(row['shares'] is None for row in rows):
            result['notices'].append('Quantités non attestées sur certaines lignes ; montant seulement recoupable.')
        result.update(status='ok', session=session, rows=rows, market_closed=closed)
        if not closed:
            result['notices'].append('Marché non confirmé clôturé ; ne pas valider une clôture finale.')
    except (ValueError, TypeError, OverflowError):
        # Stable classifications only: never expose source bodies or credentials.
        result['notices'].append('Réponse Wafabourse invalide : identité, séance, périmètre ou chiffres non vérifiables.')
    return result


def fetch_wafabourse(*, expected_session=None, observed_at=None, opener=None, timeout=15):
    """Two public frontend requests, bounded bodies and no automatic retries."""
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()
    if opener is None:
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), _NoRedirect())
    headers = {'Accept': 'application/json', 'Referer': SOURCE_URL,
               'User-Agent': 'BVC-Nour-public-market-reconciliation/1.0'}

    def request_json(path, *, body=None, extra_headers=None):
        request = urllib.request.Request(ORIGIN + path, data=body,
                                        headers={**headers, **(extra_headers or {})})
        with opener.open(request, timeout=min(max(timeout, 1), 15)) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('response_too_large')
        return json.loads(raw)

    try:
        token_payload = request_json('/api/proxy/token')
        token = token_payload.get('token') if isinstance(token_payload, dict) else None
        if not isinstance(token, str) or not token or len(token) > 8192 or '\n' in token or '\r' in token:
            raise ValueError('invalid_public_frontend_token')
        body = {'ACTIONS': [{'ACTION': {'NAME': ACTION, 'TYPE': 'SELECT', 'VALUE': ACTION},
                             'PARAMS': [{'NAME': 'TypeStocks_', 'TYPE': 'I', 'VALUE': 1},
                                        {'NAME': 'NumseqMin_', 'TYPE': 'I', 'VALUE': '0'},
                                        {'NAME': 'NumseqMax_', 'TYPE': 'I', 'VALUE': '0'}]}]}
        payload = request_json('/api/proxy/data/JNNJ', body=json.dumps(body).encode('utf-8'),
                               extra_headers={'Content-Type': 'application/json', 'x-proxy-token': token})
        return parse_wafabourse(payload, observed_at=observed_at, expected_session=expected_session)
    except (OSError, ValueError, TypeError, urllib.error.URLError):
        result = _result(observed_at)
        result.update(status='unavailable', notices=[
            'Source publique Wafabourse indisponible ou réponse inexploitable ; aucun remplacement automatique.'])
        return result
