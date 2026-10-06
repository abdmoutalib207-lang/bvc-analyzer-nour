"""One deterministic, versioned calculation path. News and NLP contribute zero."""
from __future__ import annotations

import math
from statistics import median

SCORE_VERSION = "nour-quant-v1"


def _round(v, digits=2):
    return round(v, digits) if v is not None and math.isfinite(v) else None


def _ema(values, period):
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    for x in values[period:]:
        value += (x - value) * 2 / (period + 1)
    return value


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gain = sum(max(v, 0) for v in changes[:period]) / period
    loss = sum(max(-v, 0) for v in changes[:period]) / period
    for v in changes[period:]:
        gain = (gain * (period - 1) + max(v, 0)) / period
        loss = (loss * (period - 1) + max(-v, 0)) / period
    if gain == loss == 0:
        return 50.0
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def technical(record):
    bars = record.get("candles") or []
    # The first malformed bar blocks precise OHLC-derived indicators; no fabrication.
    clean = [b for b in bars if all(isinstance(b.get(k), (int,float)) and not isinstance(b.get(k), bool) and
                                     math.isfinite(float(b[k])) for k in ("o","h","l","c","v"))
             and b["c"] > 0 and b["h"] >= max(b["o"], b["c"], b["l"])
             and b["l"] <= min(b["o"], b["c"]) and b["v"] >= 0]
    resumed = bool(record.get("resumed_recently"))
    if resumed:
        n = record.get("sessions_since_resume")
        clean = clean[-n:] if isinstance(n, int) and n > 0 else []
    closes = [float(b["c"]) for b in clean]
    volumes = [float(b["v"]) for b in clean]
    n = len(clean)
    last = closes[-1] if closes else None
    avg = lambda p: sum(closes[-p:])/p if n >= p else None
    prev = clean[-21:-1] if n >= 21 else []
    trs = []
    for i in range(1,n):
        b = clean[i]
        trs.append(max(b["h"]-b["l"], abs(b["h"]-closes[i-1]), abs(b["l"]-closes[i-1])))
    avg_vol = median(volumes[-21:-1]) if n >= 21 and any(volumes[-21:-1]) else None
    macd = (_ema(closes,12)-_ema(closes,26)) if n >= 26 else None
    # Signal EMA must use the full MACD sequence, not the latest value alone.
    macd_series = [(_ema(closes[:i],12)-_ema(closes[:i],26)) for i in range(26,n+1)]
    signal = _ema(macd_series,9) if len(macd_series) >= 9 else None
    return {"sessions": n, "sma20": _round(avg(20)), "sma50": _round(avg(50)),
            "sma200": _round(avg(200)), "rsi14": _round(_rsi(closes)),
            "macd": _round(macd), "macd_signal": _round(signal),
            "atr14": _round(sum(trs[-14:])/14 if len(trs)>=14 else None),
            "return20_pct": _round((last/closes[-21]-1)*100 if n>=21 else None),
            "support20": _round(min(b["l"] for b in prev) if prev else None),
            "resistance20": _round(max(b["h"] for b in prev) if prev else None),
            "volume_vs_median20": _round(volumes[-1]/avg_vol if avg_vol else None),
            "limited_by_resumption": resumed}


def fundamentals(record, facts):
    """Single implementation shared by every consumer."""
    from .fundamentals import calculate
    return calculate(record, facts)


def canonical_score(quality, tech, fundamental):
    """Descriptive 0..100 research score, guarded and never a buy/sell order.

    Factors have fixed weights; unavailable factors do not inherit missing weight.
    Coverage records how much of the intended 100 points has real evidence.
    """
    if quality.get("decision") in {"SUSPENDU", "INDISPONIBLE"}:
        return {"value": None, "state": "NON_CALCULABLE", "version": SCORE_VERSION,
                "coverage_pct": 0, "contributors": {}, "nlp_weight": 0}
    contributors = {}
    price = quality.get("price")
    if price and tech.get("sma20") is not None:
        contributors["tendance20"] = {"weight": 20, "points": 20 if price>tech["sma20"] else 0}
    if price and tech.get("sma50") is not None:
        contributors["tendance50"] = {"weight": 15, "points": 15 if price>tech["sma50"] else 0}
    if tech.get("rsi14") is not None:
        rsi = tech["rsi14"]
        contributors["momentum"] = {"weight": 15, "points": 15 if 45<=rsi<=70 else 7.5 if 30<=rsi<45 else 0}
    if tech.get("volume_vs_median20") is not None:
        ratio=tech["volume_vs_median20"]
        contributors["activité"] = {"weight": 10, "points": 10 if .8<=ratio<=3 else 5 if ratio<.8 else 2}
    liq=quality.get("liquidity") or {}
    if liq.get("ready") and liq.get("median_turnover_mad_estimated") is not None:
        amount=liq["median_turnover_mad_estimated"]
        contributors["liquidité"] = {"weight": 20, "points": 20 if amount>=5e6 else 10 if amount>=1e6 else 0}
    if fundamental.get("roe_pct") is not None:
        roe=fundamental["roe_pct"]
        contributors["rentabilité"] = {"weight": 20, "points": 20 if roe>=12 else 10 if roe>=5 else 0}
    coverage=sum(x["weight"] for x in contributors.values())
    value=_round(sum(x["points"] for x in contributors.values()) / coverage * 100) if coverage else None
    state="CALCULABLE" if quality.get("decision")=="OBSERVABLE" and coverage>=70 else "PARTIEL"
    if state=="PARTIEL":
        value=None  # Partial factor coverage must not look like a ranked score.
    return {"value":value,"state":state,"version":SCORE_VERSION,
            "coverage_pct":coverage,"contributors":contributors,"nlp_weight":0}
