"""Explicit, replayable extension of MASI closes; never overwrite Nour's history."""
import copy
import math
from datetime import date

from .market import CANCELLED_SESSIONS


def extend_history(history, source, provenance, asof):
    cutoff = date.fromisoformat(asof)
    existing = history.get('seances', {})
    incoming = source.get('seances')
    if not isinstance(incoming, dict):
        raise ValueError('Historique source MASI absent')
    additions, common, max_delta = {}, 0, 0.0
    for day, value in incoming.items():
        parsed = date.fromisoformat(day)
        if (parsed.isoformat() != day or parsed > cutoff or parsed.weekday() > 4
                or day in CANCELLED_SESSIONS or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0):
            raise ValueError(f'Séance MASI inadmissible : {day}')
        if day in existing:
            delta = abs(existing[day] - value)
            if delta > .01:
                raise ValueError(f'Clôture MASI divergente : {day}')
            common += 1
            max_delta = max(max_delta, delta)
        else:
            additions[day] = value
    result = copy.deepcopy(history)
    if not additions:
        return result
    result['seances'] = dict(sorted({**existing, **additions}.items()))
    audit = {**copy.deepcopy(provenance), 'checked_at': asof,
             'added': len(additions), 'from': min(additions), 'to': max(additions),
             'common_sessions': common, 'max_common_delta_points': max_delta,
             'existing_closes_preserved': True}
    result.setdefault('provenance', {}).setdefault('history_extensions', []).append(audit)
    return result
