"""Transparent descriptive pilot engine. No automated buy/sell signal."""
from datetime import date
from math import ceil, sqrt, isfinite
from statistics import median, stdev
from .analytics import technical, fundamentals, canonical_score, SCORE_VERSION, ordered_sum
from .fundamentals import coverage
from .statistics import describe
from .sector_methods import guidance
from .publication import history_readiness
from .resilience import validate_fixture, guarded, issue
from .sector_calculators import calculate_sector


def _mean(items):
    return ordered_sum(items) / len(items) if items else None


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
            if day.isoformat() > asof:
                issues.append("Ligne future exclue")
                continue
            if any(isinstance(bar.get(k), bool) for k in ('o', 'h', 'l', 'c', 'v')):
                raise ValueError('Boolean price')
            o, h, l, c, v = (float(bar[k]) for k in ("o", "h", "l", "c", "v"))
            if not all(isfinite(x) for x in (o,h,l,c,v)) or day.isoformat() in seen or h < l or min(o, h, l, c) <= 0 or v < 0:
                issues.append(f"Ligne incohérente ou doublon : {bar.get('d')}")
                continue
            seen.add(day.isoformat())
            if not l <= o <= h:
                invalid_open.append(day.isoformat())
            if not l <= c <= h:
                invalid_close.append(day.isoformat())
                continue
            valid.append({"d": day.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": v})
        except (KeyError, ValueError, TypeError, OverflowError):
            issues.append("Ligne illisible")
    if [bar["d"] for bar in valid] != sorted(bar["d"] for bar in valid):
        issues.append("Dates historiques non croissantes")
        valid.sort(key=lambda bar: bar["d"])

    age_days = None
    if valid and record.get("price_asof"):
        try:
            age_days = (date.fromisoformat(asof) - date.fromisoformat(record["price_asof"])).days
        except (TypeError, ValueError):
            issues.append("Date de cours illisible")
    if age_days is None or age_days < 0 or age_days > 4 or record.get("stale"):
        issues.append("Cours absent, futur ou périmé à la date du rapport")
    try:
        price = None if isinstance(record.get('price'), bool) else float(record.get("price"))
    except (TypeError, ValueError, OverflowError):
        price = None
    if price is not None and (not isfinite(price) or price <= 0):
        price = None
    if (not valid or price is None or abs(valid[-1]["c"] - price) > .001
            or valid[-1]["d"] != record.get("price_asof")):
        issues.append("Désaccord entre séance, clôture et instantané")
    if invalid_open:
        issues.append(f"{len(invalid_open)} ouverture(s) hors fourchette : OHLC non fiables pour ATR / spread")
    if invalid_close:
        issues.append(f"{len(invalid_close)} clôture(s) hors fourchette rejetée(s)")

    # Do not mix pre-suspension volumes with post-resumption execution capacity.
    resumed = bool(record.get("resumed_recently"))
    since_resume = record.get("sessions_since_resume")
    resume_count_valid = (isinstance(since_resume, int)
                          and not isinstance(since_resume, bool) and since_resume > 0)
    if resumed:
        liquidity_bars = valid[-min(since_resume, len(valid)):] if resume_count_valid else []
    else:
        liquidity_bars = valid[-20:]
    window = liquidity_bars[-20:]
    active = [bar for bar in window if bar["v"] > 0]
    estimated = [bar["c"] * bar["v"] for bar in active]
    excluding_top5 = sorted(estimated)[:-5] if len(estimated) >= 10 else []
    integrity_block = bool(invalid_close or any("Ligne" in issue or "Dates" in issue for issue in issues))
    trust_block = any("périmé" in issue or "Désaccord" in issue for issue in issues)
    liquidity_ready = len(active) >= 10 and len(window) >= 10 and not record.get("suspended") and not integrity_block and not trust_block and not (resumed and not resume_count_valid)
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
    documented_suspension = (record.get('suspended') and not raw
        and (record.get('issuer_status') or {}).get('trading_status') == 'suspended')
    if documented_suspension:
        issues = ['Cotation suspendue : absence de transactions documentée ; aucun cours récent attesté.']
    return {
        "symbol": symbol, "name": record.get("name"), "sector": record.get("sector"),
        "issuer_status": record.get('issuer_status'),
        "history_provenance": record.get('history_provenance'),
        "reference_quote": record.get('reference_quote'),
        "decision": verdict,
        "decision_type": "data_readiness_only",
        "asof": record.get("price_asof"), "age_calendar_days": age_days,
        "price": price, "price_source": record.get("price_source"),
        'price_source_datetime': record.get('price_source_datetime'),
        'price_collected_at': record.get('price_collected_at'),
        'source_checked_at': record.get('source_checked_at'),
        'source_check_status': record.get('source_check_status'),
        'price_validated_at': record.get('price_validated_at'),
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


_fallback_analyze = analyze
_fallback_technical = technical


def build_report(fixture, asof=None, quantity=1000, facts=None, news=None):
    asof = asof or date.today().isoformat()
    facts = facts or {}
    validate_fixture(fixture)
    results = []
    for symbol in fixture["symbols"]:
        rec = fixture['records'].get(symbol) or {'symbol':symbol, 'candles':[]}
        control = {'symbol':symbol}
        item = guarded(control, 'analysis', lambda: analyze(rec, asof, quantity),
            lambda: _fallback_analyze({'symbol':symbol,'name':rec.get('name'),
                'sector':rec.get('sector'),'candles':[]}, asof, quantity))
        if control.get('resilience'):
            item['resilience'] = control['resilience']
            issue(item, 'price', 'issuer_analysis_unavailable', 'Analyse du titre suspendue.',
                  ['liquidity','trend'])
        raw_bars = rec.get('candles') if isinstance(rec.get('candles'), list) else []
        dated = {**rec, 'candles': [b for b in raw_bars
                                  if isinstance(b, dict) and isinstance(b.get('d'), str) and b['d'] <= asof]}
        item["technical"] = guarded(item, 'technical', lambda: technical(dated),
                                    lambda: _fallback_technical({'candles':[]}))
        market_problem = rec.get('quarantined_market')
        if market_problem:
            item.update(price=None, day_shares=None, day_turnover_mad_actual=None,
                        decision='INDISPONIBLE', price_source_datetime=None)
            item['technical'] = _fallback_technical({'candles':[]})
            item['liquidity'].update(ready=False, capacity_shares_per_session_at_10pct=None,
                                    exit_days_at_10pct=None, median_shares=None,
                                    median_turnover_mad_estimated=None,median_turnover_ex_top5_mad_estimated=None)
            issue(item,'source','market_line_quarantined',market_problem['reason'],
                  ['market','technical','liquidity'],source=market_problem.get('source'),evidence=market_problem)
            item['quality']['issues'].append(market_problem['reason'])
        item["history_readiness"] = history_readiness(item)
        # Imported current facts are not a point-in-time financial database.
        # A historical build must not quietly use the current fact snapshot.
        historical = asof < str(fixture.get('snapshot_updated', ''))[:10]
        # A quote can have a numeric price yet be rejected by the market
        # integrity checks (stale, future, or inconsistent with last close).
        # It must never be used to price annual EPS/book value in that case.
        quote_for_valuation = ({**rec, 'stale': True, 'price':None if market_problem else rec.get('price')}
                               if item['decision'] in ('INDISPONIBLE', 'SUSPENDU')
                               else rec)
        item["fundamental"] = guarded(item, 'fundamental', lambda: fundamentals(
            quote_for_valuation, None if historical else facts.get(symbol), asof=asof),
            lambda: _empty_fundamentals(asof))
        status = item.get('issuer_status') or {}
        if status and not item['fundamental'].get('document_url'):
            item['fundamental']['warnings'].append(status['reason'])
        if historical:
            item['fundamental']['warnings'].append('Reconstruction historique : fondamentaux actuels exclus faute de disponibilité datée vérifiée.')
        item["historical_statistics"] = guarded(item, 'historical_statistics', lambda: describe(dated),
            lambda: {'status':'unavailable','horizons':[], 'reason':'Erreur locale de calcul.'})
        if market_problem:
            item['historical_statistics']={'status':'unavailable','horizons':[],'reason':'Cotation ou volume en conflit ; historique courant non validé.'}
            issue(item,'historical_statistics','market_line_quarantined',market_problem['reason'],['historical_statistics'])
        item["canonical_score"] = guarded(item, 'canonical_score',
            lambda: canonical_score(item, item["technical"], item["fundamental"]),
            lambda: {'value':None,'state':'NON_CALCULABLE','version':SCORE_VERSION,
                     'coverage_pct':0,'contributors':{},'nlp_weight':0})
        # Descriptive industry-specific review prompts only; not a financial fact
        # and not an input to the score or to the technical indicators.
        item["sector_guidance"] = guidance(symbol, {"sector": rec.get("sector")})
        item['sector_indicators'] = guarded(item,'sector_indicators',
            lambda: calculate_sector(symbol,rec,None if historical else facts.get(symbol),asof),
            lambda: {'version':'nour-sector-calculators-v1','symbol':symbol,
                     'family':item['sector_guidance']['family'],'metrics':{},'status':'unavailable',
                     'used_for_score':False,'documents_certified':False})
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


def _empty_fundamentals(asof):
    from .fundamentals import calculate
    return calculate({}, None, asof=asof)
