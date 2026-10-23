"""Independent CDG closing-session adapter and transactional market import.

Source codes are an explicit reviewed mapping: SNA is Stokvis, SID is Sonasid.
No missing OHLC value is inferred from opening or closing prices.
"""
from __future__ import annotations

import copy
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SOURCE_URL = "https://www.cdgcapitalbourse.ma/api/"
CASABLANCA = ZoneInfo("Africa/Casablanca")
CANCELLED_SESSIONS = {"2026-09-17"}


def request_body():
    params = [("Lang_", "S", "fr"), ("Espace_", "I", "1"),
              ("IdPartener_", "I", "1"), ("TypeStocks_", "S", "1"),
              ("TypeCotation_", "S", "0")]
    return {"ACTIONS": [{"ACTION": {"NAME": "MARKET-RESUME", "TYPE": "SELECT",
                                     "VALUE": "MARKET-RESUME"},
                         "PARAMS": [dict(NAME=n, TYPE=t, VALUE=v) for n, t, v in params]}]}


def _fetch_cdg_once(timeout=30):
    req = Request(SOURCE_URL, data=json.dumps(request_body()).encode(),
                  headers={"Content-Type": "application/json",
                           "User-Agent": "BVCAnalyzerNour/1.0 (+public research)",
                           "Referer": "https://www.cdgcapitalbourse.ma/Bourse/market",
                           "Origin": "https://www.cdgcapitalbourse.ma"})
    with urlopen(req, timeout=timeout) as response:
        payload = json.load(response)
    block = payload[0]["MARKET-RESUME"]
    if block.get("Valid") is not True or not isinstance(block.get("Data"), list):
        raise ValueError("Réponse CDG invalide")
    lines = block["Data"]
    if len(lines) == 1 and isinstance(lines[0], list):
        lines = lines[0]
    if not all(isinstance(line, dict) for line in lines):
        raise ValueError("Format CDG inconnu")
    return lines


def fetch_cdg(timeout=30):
    from .transactions import retry_transient
    return retry_transient(lambda: _fetch_cdg_once(timeout))


def numeric(value):
    if isinstance(value,bool):return None
    try:
        v = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return v if math.isfinite(v) else None


def session_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%d/%m/%Y").date().isoformat()
    except (ValueError, TypeError):
        return None


def normalized_quote(line, ticker):
    day = session_date(line.get("DateDernierCours"))
    c, o, h, l = (numeric(line.get(key)) for key in
                  ("Cours", "Ouverture", "PlusHaut", "PlusBas"))
    shares = numeric(line.get("QteEchangee"))
    amount = numeric(line.get("Volumes"))
    if not day or day in CANCELLED_SESSIONS or c is None or c <= 0 or not shares:
        return None  # A reference price without an exchange is not a candle.
    if None in (o, h, l) or min(o, h, l) <= 0 or h < max(o, c) or l > min(o, c):
        raise ValueError(f"{ticker} {day}: extrêmes/ouverture absents ou incohérents")
    if shares <= 0 or not shares.is_integer() or amount is None or amount <= 0:
        raise ValueError(f"{ticker} {day}: volume monétaire ou quantité invalide")
    # A wildly divergent monetary turnover usually means a field mapping error.
    if not l * shares * .95 <= amount <= h * shares * 1.05:
        raise ValueError(f"{ticker} {day}: montant incompatible avec les transactions")
    try:
        stamp = datetime.strptime(str(line.get('DateDernierCours')), '%d/%m/%Y %H:%M:%S')
        source_datetime = stamp.strftime('%d/%m/%Y %H:%M:%S') if stamp.date().isoformat() == day else None
    except (TypeError, ValueError):
        source_datetime = None
    return {"bar": {"d": day, "o": o, "h": h, "l": l, "c": c, "v": int(shares),
                    "turnover_mad": amount}, "source": SOURCE_URL, 'source_datetime': source_datetime}


def import_session(fixture, lines, code_map, now=None, minimum=20):
    """Return a new fixture or raise. Nothing in the original object is changed."""
    now = now or datetime.now(CASABLANCA)
    today = now.astimezone(CASABLANCA).date().isoformat()
    if len(set(code_map.values())) != len(code_map):
        raise ValueError("Codes officiels en collision")
    inverse = {code: ticker for ticker, code in code_map.items()}
    quote_by_ticker = {}
    rejected, seen = [], set()
    def reject(ticker, reason, line):
        quote_by_ticker.pop(ticker, None)
        rejected.append({'symbol':ticker,'domain':'source','code':'invalid_source_row',
            'reason':reason,'observed_at':now.isoformat(),'source':SOURCE_URL,
            'observed':{k:line.get(k) for k in ('Symbol','DateDernierCours','Cours','Volumes','QteEchangee')},
            'resolution':'pending_review'})
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError('Schéma général CDG invalide')
        ticker = inverse.get(str(line.get("Symbol") or "").strip().upper())
        if ticker not in fixture["records"]:
            continue
        if ticker in seen:
            reject(ticker, 'Lignes source dupliquées pour ce titre', line)
            continue
        seen.add(ticker)
        try:
            quote = normalized_quote(line, ticker)
        except (ValueError, TypeError, OverflowError) as exc:
            reject(ticker, str(exc), line)
            continue
        if quote is None:
            continue
        day = quote["bar"]["d"]
        if day > today:
            reject(ticker, 'Cotation future refusée pour ce titre', line)
            continue
        quote_by_ticker[ticker] = quote
    dates = Counter(q["bar"]["d"] for q in quote_by_ticker.values())
    eligible = [d for d, n in dates.items() if n >= minimum]
    if not eligible:
        raise ValueError(f"Aucune séance commune confirmée par {minimum} titres")
    session = max(eligible)
    if session == today and now.astimezone(CASABLANCA).hour < 16:
        raise ValueError("Séance du jour inachevée avant 16h00 Casablanca")
    # Old rows from thinly traded instruments cannot move the snapshot backwards.
    fresh = {s: q for s, q in quote_by_ticker.items() if q["bar"]["d"] == session}
    updated = copy.deepcopy(fixture)
    for ticker in seen:
        updated['records'][ticker]['source_checked_at'] = now.isoformat()
        updated['records'][ticker]['source_check_status'] = ('rejected' if any(x['symbol']==ticker for x in rejected) else 'checked')
    changed = 0
    observations_refreshed = 0
    conflicts = list(rejected)
    for ticker, quote in fresh.items():
        before=copy.deepcopy(updated['records'][ticker]);before_counts=(changed,observations_refreshed)
        try:
            rec = updated["records"][ticker]
            bar = quote["bar"]
            old_date = rec.get("price_asof") or ""
            if old_date > session:
                conflicts.append({'symbol':ticker,'reason':'Date source antérieure à l’instantané',
                                  'source':SOURCE_URL,'session':session,'resolution':'pending_review'})
                continue
            existing = next((b for b in rec["candles"] if b["d"] == session), None)
            if existing:
                differing = [k for k in ("o", "h", "l", "c", "v")
                             if float(existing[k]) != float(bar[k])]
                if differing:
                    # Never revise historical candles based on a live response. Flag
                    # the discrepancy without preventing other tickers from updating.
                    conflicts.append({"symbol": ticker, "session": session,
                                      "fields": differing,
                                      "retained": {k: existing.get(k) for k in differing},
                                      "observed": {k: bar.get(k) for k in differing},
                                      "observed_at": now.astimezone(CASABLANCA).isoformat(),
                                      "source": quote["source"],
                                      "reason": "Écrasement automatique interdit ; rapprochement documentaire requis",
                                      "resolution": "pending_review"})
                    continue
            else:
                if rec["candles"] and rec["candles"][-1]["d"] > session:
                    conflicts.append({'symbol':ticker,'reason':'Historique désordonné',
                                      'source':SOURCE_URL,'session':session,'resolution':'pending_review'})
                    continue
                rec["candles"].append(bar)
                changed += 1
            rec.update(price=bar["c"], price_asof=session, price_source="CDG Capital Bourse",
                       price_source_datetime=quote.get('source_datetime'),
                       price_collected_at=now.astimezone(CASABLANCA).isoformat(),
                       price_validated_at=now.astimezone(CASABLANCA).isoformat(),
                       day_turnover_mad=bar["turnover_mad"], day_shares=bar["v"],
                       stale=False, suspended=False, full_history_count_reported=len(rec["candles"]))
            observations_refreshed += 1
            if ticker == "CMT":
                count = sum(b["d"] >= "2026-09-16" for b in rec["candles"])
                rec["sessions_since_resume"] = count
                rec["resumed_recently"] = count < 50
        except MemoryError:raise
        except Exception as exc:
            updated['records'][ticker]=before
            changed,observations_refreshed=before_counts
            conflicts.append({'symbol':ticker,'session':session,'source':SOURCE_URL,'observed_at':now.isoformat(),
                'reason':'Import local suspendu : '+type(exc).__name__,'resolution':'pending_review'})
    for problem in conflicts:
        updated['records'][problem['symbol']]['source_check_status']='retained_conflict'
    updated["snapshot_updated"] = now.astimezone(CASABLANCA).isoformat()
    updated["market"]["last_session"] = session
    # The index is not present in MARKET-RESUME. Never relabel the old MASI.
    if updated["market"].get("masi"):
        updated["market"]["masi"]["stale"] = (
            updated["market"]["masi"].get("asof") != session)
    return updated, {"session": session, "active_quotes": len(fresh), "new_bars": changed,
                     'observations_refreshed': observations_refreshed,
                     "source": SOURCE_URL, "ignored_old_quotes": len(quote_by_ticker)-len(fresh),
                     "conflicts": conflicts}


def capture_intraday(fixture, lines, code_map, now=None):
    """Capture today's exchanges separately; do not mutate records or candles."""
    now = (now or datetime.now(CASABLANCA)).astimezone(CASABLANCA)
    today = now.date().isoformat()
    if len(set(code_map.values())) != len(code_map):
        raise ValueError("Codes officiels en collision")
    if now.weekday() >= 5 or today in CANCELLED_SESSIONS or now.hour >= 16:
        raise ValueError("Collecte intrajournalière hors fenêtre autorisée")
    inverse = {code: ticker for ticker, code in code_map.items()}
    quotes, rejected, seen = {}, [], set()
    for line in lines:
        ticker = inverse.get(str(line.get("Symbol") or "").strip().upper())
        if ticker not in fixture["records"]:
            continue
        if ticker in seen:
            quotes.pop(ticker,None)
            rejected.append({'symbol':ticker,'reason':'Lignes source dupliquées ; titre isolé'})
            continue
        seen.add(ticker)
        day = session_date(line.get("DateDernierCours"))
        if day and day > today:
            rejected.append({'symbol':ticker,'reason':'Cotation future refusée ; titre isolé'})
            continue
        if day != today:
            continue
        try:
            quote = normalized_quote(line, ticker)
        except ValueError as exc:
            rejected.append({"symbol": ticker, "reason": str(exc)})
            continue
        if quote:
            bar = quote["bar"]
            quotes[ticker] = {"price": bar["c"], "asof": bar["d"], "open": bar["o"],
                              'source_datetime': quote.get('source_datetime'),
                              "high": bar["h"], "low": bar["l"], "shares": bar["v"],
                              "turnover_mad": bar["turnover_mad"], "provisional": True,
                              "source": SOURCE_URL}
    return {"schema_version": 1, "session": today, "observed_at": now.isoformat(),
            "source": SOURCE_URL, "quotes": quotes, "rejected": rejected,
            "timestamp_kind": "collector_observation_not_exchange_timestamp"}


def atomic_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(path)
