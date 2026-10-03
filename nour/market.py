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


def fetch_cdg(timeout=30):
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


def numeric(value):
    try:
        v = float(value)
    except (ValueError, TypeError):
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
    return {"bar": {"d": day, "o": o, "h": h, "l": l, "c": c, "v": int(shares),
                    "turnover_mad": amount}, "source": SOURCE_URL}


def import_session(fixture, lines, code_map, now=None, minimum=20):
    """Return a new fixture or raise. Nothing in the original object is changed."""
    now = now or datetime.now(CASABLANCA)
    today = now.astimezone(CASABLANCA).date().isoformat()
    if len(set(code_map.values())) != len(code_map):
        raise ValueError("Codes officiels en collision")
    inverse = {code: ticker for ticker, code in code_map.items()}
    quote_by_ticker = {}
    for line in lines:
        ticker = inverse.get(str(line.get("Symbol") or "").strip().upper())
        if ticker not in fixture["records"]:
            continue
        quote = normalized_quote(line, ticker)
        if quote is None:
            continue
        day = quote["bar"]["d"]
        if day > today:
            raise ValueError("Cotation future refusée")
        if ticker in quote_by_ticker:
            raise ValueError(f"{ticker}: collision de lignes CDG")
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
    changed = 0
    conflicts = []
    for ticker, quote in fresh.items():
        rec = updated["records"][ticker]
        bar = quote["bar"]
        old_date = rec.get("price_asof") or ""
        if old_date > session:
            raise ValueError(f"{ticker}: date source antérieure à l'instantané")
        existing = next((b for b in rec["candles"] if b["d"] == session), None)
        if existing:
            differing = [k for k in ("o", "h", "l", "c", "v")
                         if float(existing[k]) != float(bar[k])]
            if differing:
                # Never revise historical candles based on a live response. Flag
                # the discrepancy without preventing other tickers from updating.
                conflicts.append({"symbol": ticker, "session": session,
                                  "fields": differing})
                continue
        else:
            if rec["candles"] and rec["candles"][-1]["d"] > session:
                raise ValueError(f"{ticker}: historique désordonné")
            rec["candles"].append(bar)
            changed += 1
        rec.update(price=bar["c"], price_asof=session, price_source="CDG Capital Bourse",
                   day_turnover_mad=bar["turnover_mad"], day_shares=bar["v"],
                   stale=False, suspended=False, full_history_count_reported=len(rec["candles"]))
        if ticker == "CMT":
            count = sum(b["d"] >= "2026-09-16" for b in rec["candles"])
            rec["sessions_since_resume"] = count
            rec["resumed_recently"] = count < 50
    updated["snapshot_updated"] = now.astimezone(CASABLANCA).isoformat()
    updated["market"]["last_session"] = session
    # The index is not present in MARKET-RESUME. Never relabel the old MASI.
    if updated["market"].get("masi"):
        updated["market"]["masi"]["stale"] = (
            updated["market"]["masi"].get("asof") != session)
    return updated, {"session": session, "active_quotes": len(fresh), "new_bars": changed,
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
            raise ValueError(f"{ticker}: collision de lignes CDG")
        seen.add(ticker)
        day = session_date(line.get("DateDernierCours"))
        if day and day > today:
            raise ValueError("Cotation future refusée")
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
                              "high": bar["h"], "low": bar["l"], "shares": bar["v"],
                              "turnover_mad": bar["turnover_mad"], "provisional": True,
                              "source": SOURCE_URL}
    return {"schema_version": 1, "session": today, "observed_at": now.isoformat(),
            "source": SOURCE_URL, "quotes": quotes, "rejected": rejected,
            "timestamp_kind": "collector_observation_not_exchange_timestamp"}


def atomic_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(path)
