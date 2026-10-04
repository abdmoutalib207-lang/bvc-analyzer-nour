"""Unconditional historical frequencies, never probabilities of a future price."""
from math import sqrt, isfinite
from statistics import median


def describe(record):
    bars = record.get('candles') or []
    if record.get('resumed_recently'):
        n = record.get('sessions_since_resume')
        bars = bars[-n:] if isinstance(n,int) and not isinstance(n,bool) and n>0 else []
    # An invalid close breaks the sequence rather than shortening the horizon.
    closes = [b.get('c') if isinstance(b.get('c'),(int,float)) and not isinstance(b.get('c'),bool)
              and isfinite(b['c']) and b['c']>0 and b.get('l',float('inf'))<=b['c']<=b.get('h',0)
              else None for b in bars]
    output = []
    for horizon in (1,5,20):
        samples = [(closes[i]/closes[i-horizon]-1)*100
                   for i in range(horizon,len(closes),horizon)
                   if all(v is not None for v in closes[i-horizon:i+1])]
        n = len(samples)
        if n<30:
            output.append(dict(horizon_sessions=horizon, observations=n, state='insufficient',
                               positive_frequency_pct=None, median_return_pct=None, wilson95_pct=None))
            continue
        ordered = sorted(samples)
        positive = sum(x>0 for x in samples)
        p, z = positive/n, 1.95996398454
        center = (p+z*z/(2*n))/(1+z*z/n)
        half = z*sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        output.append(dict(horizon_sessions=horizon, observations=n, state='historical_only',
            positive_frequency_pct=round(p*100,2), median_return_pct=round(median(samples),2),
            p10_return_pct=round(ordered[int((n-1)*.1)],2), p90_return_pct=round(ordered[int((n-1)*.9)],2),
            wilson95_pct=[round((center-half)*100,2),round((center+half)*100,2)]))
    return dict(method='non_overlapping_returns_v1', horizons=output,
        first_session=bars[0]['d'] if bars else None, last_session=bars[-1]['d'] if bars else None,
        note='Fréquences historiques inconditionnelles sur fenêtres non chevauchantes, sans dividendes ni frais. Intervalle de Wilson indicatif : dépendance temporelle et changements de régime non corrigés. Ni prévision, ni probabilité de la prochaine séance.')
