"""Transparent descriptive pilot engine. No automated buy/sell signal."""
from datetime import date
from math import ceil, sqrt
from statistics import median, stdev
from .analytics import technical, fundamentals, canonical_score, SCORE_VERSION
from .fundamentals import coverage
from .statistics import describe


def _mean(items):
    return sum(items) / len(items) if items else None


def _round(value, digits=2):
    return round(value, digits) if value is not None else None


def analyze(record, asof, quantity=1000):
    symbol = record["symbol"]
    raw = record.get("candles") or []
    valid = []
    issues = []
    invalid_open = []
    invalid_close = []
    seen = set()
    for bar in raw:
        try:
            day = date.fromisoformat(bar["d"])
            o, h, l, c, v = (float(bar[k]) for k in ("o", "h", "l", "c", "v"))
            if day.isoformat() in seen or h < l or min(o, h, l, c) < 0 or v < 0:
                issues.append(f"Ligne incohérente ou doublon : {bar.get('d')}")
                continue
            seen.add(day.isoformat())
            if not l <= o <= h:
                invalid_open.append(day.isoformat())
            if not l <= c <= h:
                invalid_close.append(day.isoformat())
                continue
            valid.append({"d": day.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": v})
        except (KeyError, ValueError, TypeError):
            issues.append("Ligne illisible")
    if [bar["d"] for bar in valid] != sorted(bar["d"] for bar in valid):
        issues.append("Dates historiques non croissantes")
        valid.sort(key=lambda bar: bar["d"])

    age_days = None
    if valid and record.get("price_asof"):
        age_days = (date.fromisoformat(asof) - date.fromisoformat(record["price_asof"])).days
    if age_days is None or age_days < 0 or age_days > 4 or record.get("stale"):
        issues.append("Cours absent, futur ou périmé à la date du rapport")
    if not valid or abs(valid[-1]["c"] - float(record.get("price") or 0)) > .001 or valid[-1]["d"] != record.get("price_asof"):
        issues.append("Désaccord entre séance, clôture et instantané")
    if invalid_open:
        issues.append(f"{len(invalid_open)} ouverture(s) hors fourchette : OHLC non fiables pour ATR / spread")
    if invalid_close:
        issues.append(f"{len(invalid_close)} clôture(s) hors fourchette rejetée(s)")

    # Do not mix pre-suspension volumes with post-resumption execution capacity.
    resumed = bool(record.get("resumed_recently"))
    since_resume = record.get("sessions_since_resume")
    liquidity_bars = valid[-min(int(since_resume), len(valid)):] if resumed and isinstance(since_resume, int) and since_resume > 0 else valid[-20:]
    window = liquidity_bars[-20:]
    active = [bar for bar in window if bar["v"] > 0]
    estimated = [bar["c"] * bar["v"] for bar in active]
    excluding_top5 = sorted(estimated)[:-5] if len(estimated) >= 10 else []
    integrity_block = bool(invalid_close or any("Ligne" in issue or "Dates" in issue for issue in issues))
    trust_block = any("périmé" in issue or "Désaccord" in issue for issue in issues)
    liquidity_ready = len(active) >= 10 and len(window) >= 10 and not record.get("suspended") and not integrity_block and not trust_block and not (resumed and not isinstance(since_resume, int))
    shares_median = median([bar["v"] for bar in active]) if active else None
    turnover_median = median(estimated) if estimated else None
    capacity = .10 * shares_median if liquidity_ready and shares_median else None
    exit_days = ceil(quantity / capacity) if capacity and quantity > 0 else None
    closes = [bar["c"] for bar in valid]
    changes = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1] > 0]
    last20 = changes[-20:]
    # Avoid mixing price regimes across a suspension: technical output is withheld.
    trend_ready = len(closes) >= 21 and not resumed and not record.get("suspended") and not any("périmé" in issue or "Désaccord" in issue for issue in issues)
    if resumed:
        issues.append(f"Reprise récente : {since_resume} séances ; tendance antérieure non comparable")
    if len(valid) < 50:
        issues.append(f"Historique limité à {len(valid)} séances dans l'extrait")
    if not liquidity_ready:
        issues.append("Liquidité récente insuffisante pour estimer la capacité de sortie")

    if record.get("suspended"):
        verdict = "SUSPENDU"
    elif any("périmé" in issue or "Désaccord" in issue for issue in issues):
        verdict = "INDISPONIBLE"
    elif liquidity_ready and trend_ready and not invalid_close and not issues:
        verdict = "OBSERVABLE"
    else:
        verdict = "LIMITÉ"
    return {
        "symbol": symbol, "name": record.get("name"),
        "decision": verdict,
        "decision_type": "data_readiness_only",
        "asof": record.get("price_asof"), "age_calendar_days": age_days,
        "price": record.get("price"), "price_source": record.get("price_source"),
        "day_turnover_mad_actual": record.get("day_turnover_mad"),
        "day_shares": record.get("day_shares"),
        "quality": {
            "candles_in_extract": len(raw), "full_history_count_reported": record.get("full_history_count_reported"),
            "usable_close_bars": len(valid), "invalid_open_count": len(invalid_open),
            "invalid_close_count": len(invalid_close), "rejected_bars": len(raw) - len(valid),
            "invalid_open_examples": invalid_open[:3], "issues": issues,
        },
        "liquidity": {
            "window_sessions": len(window), "active_sessions": len(active),
            "median_shares": _round(shares_median), "median_turnover_mad_estimated": _round(turnover_median),
            "median_turnover_ex_top5_mad_estimated": _round(median(excluding_top5) if excluding_top5 else None),
            "capacity_shares_per_session_at_10pct": _round(capacity),
            "exit_days_at_10pct": exit_days, "scenario_shares": quantity,
            "ready": liquidity_ready, "post_resume_only": resumed,
        },
        "trend": {
            "ready": trend_ready, "ma20": _round(_mean(closes[-20:]) if trend_ready else None),
            "change_20_sessions_pct": _round((closes[-1] / closes[-21] - 1) * 100 if trend_ready and closes[-21] else None),
            "realized_volatility_20d_pct": _round(stdev(last20) * sqrt(252) * 100 if trend_ready and len(last20) == 20 else None),
        },
        "close_series_last_60": closes[-60:],
        "close_dates_last_60": [bar["d"] for bar in valid[-60:]],
        "legacy_comparison": {"sig": record.get("legacy_sig"), "sigBvc": record.get("legacy_sig_bvc")},
    }


def build_report(fixture, asof=None, quantity=1000, facts=None, news=None):
    asof = asof or date.today().isoformat()
    facts = facts or {}
    results = []
    for symbol in fixture["symbols"]:
        rec = fixture["records"][symbol]
        item = analyze(rec, asof, quantity)
        item["technical"] = technical(rec)
        item["fundamental"] = fundamentals(rec, facts.get(symbol))
        item["historical_statistics"] = describe(rec)
        item["canonical_score"] = canonical_score(item, item["technical"], item["fundamental"])
        results.append(item)
    return {
        "project": fixture["project"], "schema_version": 2, "analysis_date": asof,
        "snapshot_updated": fixture["snapshot_updated"], "source_commit": fixture["source_commit"],
        "source_files": fixture["source_files"],
        "score_version": SCORE_VERSION, "news_role": "veille uniquement", "nlp_weight": 0,
        "method": "Score descriptif plafonné par la qualité et la couverture; jamais un ordre. MAD historiques estimés = cours × quantité sauf champ réel explicite; 10% de participation est un scénario.",
        "market": fixture.get("market", {}), "news": news or [], "results": results,
        "fundamental_coverage": coverage(results),
    }
