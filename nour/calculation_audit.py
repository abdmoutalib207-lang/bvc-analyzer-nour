"""Independent Decimal checks of every issuer's exported market calculations.

No import of analytics, statistics or their helpers: a shared formula bug must
not be blessed by comparing the calculator with itself. This checks arithmetic
on supplied observations, not the authenticity of prices or financial reports.
"""
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext, ROUND_CEILING
from .events import EVENTS

VERSION = 'nour-calculation-audit-v1'
TOLERANCE = Decimal('0.005001')  # Half of the published 0.01 unit, plus float noise.


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _day(value):
    try:
        return value if isinstance(value, str) and date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    return (ordered[n//2] if n % 2 else (ordered[n//2-1]+ordered[n//2])/2) if n else None


def _observations(record, asof):
    bars, issues, seen = [], [], set()
    candles = record.get('candles')
    for raw in candles if isinstance(candles,list) else []:
        if not isinstance(raw, dict) or not _day(raw.get('d')):
            issues.append('invalid_date')
            continue
        day = raw['d']
        if day > asof:
            continue
        if day in seen:
            issues.append('duplicate_date')
            continue
        seen.add(day)
        values = {k: _number(raw.get(k)) for k in ('o', 'h', 'l', 'c', 'v')}
        if (any(v is None for v in values.values()) or values['v'] < 0
                or min(values[k] for k in ('o', 'h', 'l', 'c')) <= 0
                or not values['l'] <= min(values['o'], values['c'])
                <= max(values['o'], values['c']) <= values['h']):
            issues.append('invalid_ohlcv')
            continue
        bars.append(dict(values, d=day))
    if [b['d'] for b in bars] != sorted(b['d'] for b in bars):
        issues.append('unordered_dates')
    return bars, issues


def _technical(bars):
    """Decimal reference, SMA-seeded EMA/RMA, population Bollinger variance."""
    closes = [b['c'] for b in bars]
    n = len(bars)
    average = lambda p: sum(closes[-p:])/p if n >= p else None

    def moving(values, p, multiplier):
        if len(values) < p:
            return None
        value = sum(values[:p])/p
        for x in values[p:]:
            value += multiplier*(x-value)
        return value

    changes = [b-a for a, b in zip(closes, closes[1:])]
    gain = moving([max(x, 0) for x in changes], 14, Decimal(1)/14)
    loss = moving([max(-x, 0) for x in changes], 14, Decimal(1)/14)
    rsi = None if gain is None else (Decimal(50) if gain == loss == 0 else
          Decimal(100) if loss == 0 else 100-100/(1+gain/loss))
    e12 = e26 = None
    macds = []
    for i, c in enumerate(closes, 1):
        if i == 12:
            e12 = sum(closes[:12])/12
        elif i > 12:
            e12 += (c-e12)*Decimal(2)/13
        if i == 26:
            e26 = sum(closes[:26])/26
        elif i > 26:
            e26 += (c-e26)*Decimal(2)/27
        if e26 is not None:
            macds.append(e12-e26)
    macd = macds[-1] if macds else None
    signal = moving(macds, 9, Decimal(2)/10)
    ranges = [max(b['h']-b['l'], abs(b['h']-a['c']), abs(b['l']-a['c']))
              for a, b in zip(bars, bars[1:])]
    wilder = moving(([bars[0]['h']-bars[0]['l']]+ranges) if bars else [],
                    14, Decimal(1)/14)
    middle = average(20)
    deviation = (sum((c-middle)**2 for c in closes[-20:])/20).sqrt() if middle is not None else None
    volume_base = _median([b['v'] for b in bars[-21:-1]]) if n >= 21 else None
    previous = bars[-21:-1] if n >= 21 else []
    return dict(sessions=n, sma20=middle, sma50=average(50), sma200=average(200),
        ema20=moving(closes, 20, Decimal(2)/21), ema50=moving(closes, 50, Decimal(2)/51),
        rsi14=rsi, macd=macd, macd_signal=signal,
        macd_histogram=macd-signal if signal is not None else None,
        atr14=sum(ranges[-14:])/14 if len(ranges) >= 14 else None,
        atr14_wilder=wilder, atr14_wilder_pct=100*wilder/closes[-1] if wilder is not None else None,
        bollinger_middle=middle, bollinger_upper=middle+2*deviation if deviation is not None else None,
        bollinger_lower=middle-2*deviation if deviation is not None else None,
        return20_pct=100*(closes[-1]/closes[-21]-1) if n >= 21 else None,
        support20=min(b['l'] for b in previous) if previous else None,
        resistance20=max(b['h'] for b in previous) if previous else None,
        volume_vs_median20=bars[-1]['v']/volume_base if volume_base else None)


def _statistical_samples(record, sessions, asof, horizon):
    """Independent fixed-date windows; all duplicate observations are rejected."""
    candles = record.get('candles')
    dated = [b for b in (candles if isinstance(candles,list) else []) if isinstance(b, dict)
             and _day(b.get('d')) and b['d'] <= asof]
    counts = Counter(b['d'] for b in dated)
    dates = sorted(counts)
    if record.get('resumed_recently'):
        n = record.get('sessions_since_resume')
        dates = dates[-n:] if isinstance(n, int) and not isinstance(n, bool) and n > 0 else []
    days = ([d for d in sessions if dates[0] <= d <= dates[-1]]
            if sessions is not None and dates else dates)
    values = {}
    for b in dated:
        numbers = [_number(b.get(k)) for k in ('c', 'l', 'h', 'v')]
        if (counts[b['d']] == 1 and all(v is not None and v > 0 for v in numbers)
                and numbers[1] <= numbers[0] <= numbers[2] and not record.get('suspended')):
            values[b['d']] = numbers[0]
    samples, missing, events = [], 0, 0
    boundary = EVENTS.get(record.get('symbol'))
    for start in range(0, len(days)-horizon, horizon):
        window = days[start:start+horizon+1]
        if boundary and window[0] < boundary <= window[-1]:
            events += 1
            continue
        if all(d in values for d in window):
            samples.append(100*(values[window[-1]]/values[window[0]]-1))
        else:
            missing += 1
    return samples, dict(candidate_windows=max(0, (len(days)-1)//horizon),
        excluded_missing_or_inactive_windows=missing, excluded_event_windows=events)


def audit_calculations(fixture, report):
    """Audit every output issuer, including unavailable-value contracts."""
    asof = report['analysis_date']
    if not _day(asof):
        raise ValueError('Date du rapport ISO requise')
    failures, issuers, all_checks = [], {}, 0
    expected_symbols = set(fixture['symbols'])
    output_symbols = [r['symbol'] for r in report['results']]
    if set(output_symbols) != expected_symbols or len(output_symbols) != len(expected_symbols):
        failures.append(dict(symbol='UNIVERSE', metric='symbols', actual=output_symbols,
                             expected=sorted(expected_symbols)))
    history = report.get('masi_history') or {}
    sessions = sorted(d for d, v in history.items() if _day(d) and d <= asof
                      and _number(v) is not None and _number(v) > 0) or None
    with localcontext() as context:
        context.prec = 40
        for row in report['results']:
            symbol, count = row['symbol'], 0
            record = fixture['records'].get(symbol)
            if record is None:
                continue
            before = len(failures)

            def compare(metric, actual, expected):
                nonlocal count
                count += 1
                observed = _number(actual)
                good = (actual is None if expected is None else
                        observed is not None and abs(observed-expected) <= TOLERANCE)
                if not good:
                    failures.append(dict(symbol=symbol, metric=metric, actual=str(actual),
                                         expected=str(expected) if expected is not None else None))

            bars, diagnostics = _observations(record, asof)
            technical_bars = bars
            if record.get('resumed_recently'):
                n = record.get('sessions_since_resume')
                technical_bars = bars[-n:] if isinstance(n, int) and not isinstance(n, bool) and n > 0 else []
            for key, value in _technical(technical_bars).items():
                compare('technical.'+key, row.get('technical', {}).get(key), value)
            liq = row.get('liquidity') or {}
            window = technical_bars[-20:] if record.get('resumed_recently') else bars[-20:]
            active = [b for b in window if b['v'] > 0]
            shares = _median([b['v'] for b in active])
            amounts = [b['c']*b['v'] for b in active]
            compare('liquidity.median_shares', liq.get('median_shares'), shares)
            compare('liquidity.median_turnover_mad_estimated', liq.get('median_turnover_mad_estimated'), _median(amounts))
            capacity = shares/10 if liq.get('ready') and shares else None
            compare('liquidity.capacity_shares_per_session_at_10pct', liq.get('capacity_shares_per_session_at_10pct'), capacity)
            quantity = _number(liq.get('scenario_shares'))
            exit_days = (quantity/capacity).to_integral_value(rounding=ROUND_CEILING) if capacity and quantity and quantity > 0 else None
            compare('liquidity.exit_days_at_10pct', liq.get('exit_days_at_10pct'), exit_days)
            stats = row.get('historical_statistics') or {}
            horizons = stats.get('horizons') or []
            if ([h.get('horizon_sessions') for h in horizons] != [1, 5, 20]
                    or stats.get('event_boundary') != EVENTS.get(symbol)
                    or stats.get('horizon_basis') != ('market_calendar' if sessions is not None else 'available_observations')):
                failures.append(dict(symbol=symbol, metric='statistics.contract',
                    actual='missing or inconsistent horizon/calendar/event contract',
                    expected='1/5/20; source calendar and documented event boundary'))
            for h in horizons:
                horizon = h['horizon_sessions']
                if horizon not in (1, 5, 20):
                    continue
                samples, counts = _statistical_samples(record, sessions, asof, horizon)
                n = len(samples)
                for key, value in counts.items():
                    compare(f'statistics.{horizon}.{key}', h.get(key), Decimal(value))
                compare(f'statistics.{horizon}.observations', h.get('observations'), Decimal(n))
                compare(f'statistics.{horizon}.positive_frequency_pct', h.get('positive_frequency_pct'),
                        Decimal(100)*sum(v > 0 for v in samples)/n if n >= 30 else None)
                compare(f'statistics.{horizon}.median_return_pct', h.get('median_return_pct'), _median(samples) if n >= 30 else None)
                ordered = sorted(samples)
                for p, key in [(Decimal('.1'), 'p10_return_pct'), (Decimal('.9'), 'p90_return_pct')]:
                    compare(f'statistics.{horizon}.{key}', h.get(key),
                            ordered[int((n-1)*p)] if n >= 30 else None)
                interval = h.get('wilson95_pct')
                if n >= 30:
                    p = Decimal(sum(v > 0 for v in samples))/n
                    z = Decimal('1.95996398454')
                    denominator = 1+z*z/n
                    center = (p+z*z/(2*n))/denominator
                    half = z*(p*(1-p)/n+z*z/(4*n*n)).sqrt()/denominator
                    compare(f'statistics.{horizon}.wilson_low', interval[0] if isinstance(interval, list) and len(interval) == 2 else None, 100*(center-half))
                    compare(f'statistics.{horizon}.wilson_high', interval[1] if isinstance(interval, list) and len(interval) == 2 else None, 100*(center+half))
                elif interval is not None:
                    failures.append(dict(symbol=symbol, metric=f'statistics.{horizon}.wilson', actual=str(interval), expected=None))
            issuers[symbol] = dict(checks=count, status='blocked' if len(failures) > before else 'arithmetic_checked',
                source_observation_diagnostics=dict(Counter(diagnostics)),
                financial_status=(row.get('fundamental', {}).get('financial_audit') or {}).get('status'),
                financial_blocked_metrics=(row.get('fundamental', {}).get('financial_audit') or {}).get('blocked_metrics', []))
            all_checks += count
    return dict(version=VERSION, analysis_date=asof, universe=len(expected_symbols),
        issuers_checked=len(issuers), arithmetic_checks=all_checks,
        status='blocked' if failures else 'arithmetic_checked', failures=failures, issuers=issuers,
        tolerance_absolute=str(TOLERANCE), reference_arithmetic='Decimal, precision 40',
        sources_certified=False,
        limitation='Recalcul indépendant des indicateurs, liquidité et fréquences disponibles. Ne certifie pas les données sources, tous les PDF, les ajustements de capital ni les performances futures.')
