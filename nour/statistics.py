"""Unconditional historical frequencies, never probabilities of a future price."""
from math import sqrt, isfinite
from datetime import date


def _finite_positive_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return False
    try:
        return isfinite(value)
    except (OverflowError, ValueError, TypeError):
        return False

from statistics import median


def describe(record, sessions=None, asof=None, event_boundary=None):
    """Keep missing/inactive sessions as holes on a fixed observation grid.

    With a market calendar, horizons mean market sessions, not a compressed
    list of this issuer's trades. Without one, explicitly label row horizons.
    Never use a window crossing an invalid observation or a capital event.
    """
    bars = record.get('candles') or []
    by_day, duplicates = {}, set()
    for b in bars:
        if not isinstance(b, dict):
            continue
        day = b.get('d')
        try:
            if date.fromisoformat(day).isoformat() != day:
                continue
        except (ValueError, TypeError):
            continue
        if asof and day > asof:
            continue
        if day in by_day:
            duplicates.add(day)
        by_day[day] = b
    observed = sorted(by_day)
    if record.get('resumed_recently'):
        n = record.get('sessions_since_resume')
        observed = observed[-n:] if isinstance(n,int) and not isinstance(n,bool) and n>0 else []
        by_day = {d: by_day[d] for d in observed}
        duplicates.intersection_update(observed)
    days = observed
    if sessions is not None and observed:
        days = sorted({d for d in sessions if observed[0] <= d <= observed[-1]
                       and (not asof or d <= asof)})
    closes, inactive = [], set()
    for day in days:
        b = by_day.get(day) or {}
        if not _finite_positive_number(b.get('v')):
            inactive.add(day)
        valid = (day not in duplicates and day not in inactive
                 and all(_finite_positive_number(b.get(k)) for k in ('l', 'c', 'h'))
                 and b['l'] <= b['c'] <= b['h'])
        closes.append(b['c'] if valid and not record.get('suspended') else None)
    output = []
    for horizon in (1,5,20):
        samples = []
        missing, events = 0, 0
        for i in range(horizon, len(closes), horizon):
            if event_boundary and days[i-horizon] < event_boundary <= days[i]:
                events += 1
                continue
            if not all(v is not None for v in closes[i-horizon:i+1]):
                missing += 1
                continue
            try:
                value = (closes[i] / closes[i-horizon] - 1) * 100
            except (OverflowError, ZeroDivisionError):
                missing += 1
                continue
            if isfinite(value):
                samples.append(value)
            else:
                missing += 1
        n = len(samples)
        counts = dict(candidate_windows=(len(closes)-1)//horizon if closes else 0,
                      excluded_missing_or_inactive_windows=missing,
                      excluded_event_windows=events)
        if n<30:
            output.append(dict(horizon_sessions=horizon, observations=n, state='insufficient',
                               positive_frequency_pct=None, median_return_pct=None, wilson95_pct=None,
                               **counts))
            continue
        ordered = sorted(samples)
        positive = sum(x>0 for x in samples)
        p, z = positive/n, 1.95996398454
        center = (p+z*z/(2*n))/(1+z*z/n)
        half = z*sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        output.append(dict(horizon_sessions=horizon, observations=n, state='historical_only', **counts,
            positive_frequency_pct=round(p*100,2), median_return_pct=round(median(samples),2),
            p10_return_pct=round(ordered[int((n-1)*.1)],2), p90_return_pct=round(ordered[int((n-1)*.9)],2),
            wilson95_pct=[round((center-half)*100,2),round((center+half)*100,2)]))
    return dict(method='non_overlapping_returns_v2', horizons=output,
        horizon_basis='market_calendar' if sessions is not None else 'available_observations',
        first_session=days[0] if days else None, last_session=days[-1] if days else None,
        excluded_no_exchange_or_missing_sessions=len(inactive), duplicate_sessions=len(duplicates),
        event_boundary=event_boundary,
        note=('Fréquences historiques inconditionnelles sur fenêtres non chevauchantes, sans dividendes ni frais. '
              'Séances sans échange, manquantes ou invalides et fenêtres traversant une rupture documentée exclues, sans interpolation. '
              + ('Horizons en séances du calendrier MASI. ' if sessions is not None else
                 'Calendrier MASI non fourni : horizons en observations disponibles, pas en séances quotidiennes garanties. ')
              + 'Intervalle de Wilson indicatif : dépendance temporelle et changements de régime non corrigés. Ni prévision, ni probabilité de la prochaine séance.'))
