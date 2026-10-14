"""Empirical loss tail of verified one-session returns; never a forecast.

No files, clock, score or provider dependency. Percentages are output units;
inputs are simple decimal returns. The nearest-rank convention is explicit.
"""
import math
from statistics import mean

MINIMUM = 120
NOTE = ('Mesures historiques sur une séance, hors dividendes, frais et fiscalité. '
        'La VaR est un seuil de la distribution observée, pas une perte maximale '
        'ni une garantie pour demain. La CVaR est la moyenne de la queue retenue. '
        'Dépendance temporelle, ruptures de régime et incertitude d’échantillon non corrigées.')


def historical_tail(returns):
    values = list(returns)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool)
           or not math.isfinite(v) or v <= -1 for v in values):
        raise ValueError('Rendements simples finis, numériques et supérieurs à −100 % requis.')
    n = len(values)
    result = dict(status='insufficient', observations=n, minimum=MINIMUM,
                  horizon_sessions=1, confidence_level=.95,
                  method='empirical_nearest_rank_5pct_v1',
                  var95_loss_pct=None, cvar95_loss_pct=None,
                  quantile05_return_pct=None, tail_observations=0,
                  reason=f'{n} rendements quotidiens utilisables ; minimum {MINIMUM}.', note=NOTE)
    if n < MINIMUM:
        return result
    # Integer arithmetic avoids ceil((1-.95)*120) accidentally becoming 7.
    k = (n + 19) // 20
    ordered = sorted(values)
    result.update(status='available', reason=None, tail_observations=k,
                  quantile05_return_pct=round(100*ordered[k-1], 4),
                  var95_loss_pct=round(max(0, -100*ordered[k-1]), 4),
                  cvar95_loss_pct=round(max(0, -100*mean(ordered[:k])), 4))
    return result
