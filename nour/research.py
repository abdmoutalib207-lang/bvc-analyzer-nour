"""Price-only diagnostics. No fitted weights, imputed exits or retrospective scores."""
from datetime import date
from hashlib import sha256
import json
import math
from statistics import median, stdev, mean

VERSION = 'nour-research-v1'
# Conservative boundaries copied in read-only consultation of bvc_config.py,
# principal commit eb744940faf3ddc27064819b41a190bfa7c69dfc.
# No second split adjustment. Historical segments crossing these dates excluded.
EVENTS = {'MNG': '2026-07-27', 'SOT': '2026-05-05', 'CMT': '2026-09-16'}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def prices(record, asof):
    """Duplicates and invalid rows remain holes on the common market calendar."""
    out, seen = {}, set()
    for b in record.get('candles', []):
        d = b.get('d')
        try:
            date.fromisoformat(d)
        except (ValueError, TypeError):
            continue
        if d > asof:
            continue
        if d in seen:
            out.pop(d, None)
            continue
        seen.add(d)
        if (all(finite(b.get(k)) for k in ('o', 'h', 'l', 'c', 'v'))
                and b['l'] > 0 and b['v'] >= 0
                and b['l'] <= min(b['o'], b['c']) <= max(b['o'], b['c']) <= b['h']):
            out[d] = float(b['c'])
    return out


def calendar(history, asof):
    valid = {}
    for d, value in history.items():
        try:
            date.fromisoformat(d)
        except (TypeError, ValueError):
            continue
        if d <= asof and finite(value) and value > 0:
            valid[d] = float(value)
    return dict(sorted(valid.items()))


def drawdown(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return round(100 * worst, 2)


def risk(record, history, asof):
    market = calendar(history, asof)
    days = list(market)[-253:]
    p = prices(record, asof)
    boundary = EVENTS.get(record.get('symbol'))
    if record.get('resumed_recently'):
        n = record.get('sessions_since_resume')
        available = sorted(p)
        p = {d: p[d] for d in available[-n:]} if isinstance(n, int) and n > 0 else {}
    pairs = [(d, p[d] / p[a] - 1, market[d] / market[a] - 1)
             for a, d in zip(days, days[1:]) if a in p and d in p
             and not (boundary and a < boundary <= d)]
    result = {'status': 'insufficient', 'paired_returns': len(pairs), 'minimum': 60,
              'market_calendar_sessions': len(days), 'window': '253 dernières séances MASI',
              'note': 'Cours seuls, hors dividendes. Dates adjacentes MASI appariées, aucune interpolation. Bêta et corrélation décrivent le passé.'}
    if record.get('suspended') or len(pairs) < 60:
        return result
    x, y = [r[1] for r in pairs], [r[2] for r in pairs]
    sx, sy = stdev(x), stdev(y)
    cov = sum((a-mean(x)) * (b-mean(y)) for a,b in zip(x,y)) / (len(x)-1)
    result.update(status='available', first=pairs[0][0], last=pairs[-1][0],
                  beta=round(cov / sy**2, 3) if sy else None,
                  correlation=round(cov / (sx*sy), 3) if sx and sy else None,
                  volatility_pct=round(sx*math.sqrt(252)*100, 2),
                  masi_volatility_pct=round(sy*math.sqrt(252)*100, 2))
    # Drawdown/relative performance require a complete segment, not chained
    # sparse daily returns that silently erase suspended sessions.
    complete = len(pairs) == len(days)-1 and bool(days)
    result['complete_window'] = complete
    result['drawdown_pct'] = drawdown([p[d] for d in days]) if complete else None
    result['masi_drawdown_pct'] = drawdown([market[d] for d in days]) if complete else None
    result['relative_return_pp'] = round(100*((p[days[-1]]/p[days[0]]-1)-(market[days[-1]]/market[days[0]]-1)), 2) if complete else None
    return result


def accounting_cohort(f):
    basis = (f.get('accounting_basis') or '').lower()
    scope = 'social' if 'social' in basis else 'consolidé' if 'consolid' in basis else None
    standard = ('IFRS' if 'ifrs' in basis else 'établissements de crédit' if 'établissements de crédit' in basis
                else 'Maroc / CGNC' if any(x in basis for x in ('maroc', 'cgnc')) else None)
    return (scope, standard) if scope and standard else None


def peers(results, records):
    for item in results:
        f = item['fundamental']
        cohort = accounting_cohort(f)
        sector = records[item['symbol']].get('sector')
        comparable = [r for r in results if cohort and r['symbol'] != item['symbol']
                      and records[r['symbol']].get('sector') == sector
                      and accounting_cohort(r['fundamental']) == cohort
                      and r['fundamental'].get('exercise') == f.get('exercise')
                      and r['fundamental'].get('currency') == f.get('currency') == 'MAD'
                      and r['decision'] == 'OBSERVABLE']
        metrics = {}
        for key in ('pe', 'pb', 'roe_pct'):
            others = [r for r in comparable if finite(r['fundamental'].get(key))
                      and (key == 'roe_pct' or r['fundamental'][key] > 0)]
            own = f.get(key)
            ready = len(others) >= 3 and finite(own) and item['decision'] == 'OBSERVABLE'
            values = [r['fundamental'][key] for r in others]
            metrics[key] = {'status': 'available' if ready else 'insufficient', 'value': own,
                            'other_peers': len(others), 'symbols': [r['symbol'] for r in others],
                            'median': round(median(values), 2) if ready else None,
                            'percentile': round(100*(sum(v < own for v in values)+.5*sum(v == own for v in values))/len(values), 1) if ready else None}
        item['sector_comparison'] = {'sector': sector, 'exercise': f.get('exercise'),
            'scope': cohort[0] if cohort else None, 'standard': cohort[1] if cohort else None,
            'metrics': metrics, 'note': 'Au moins trois autres titres observables, même secteur, exercice, monnaie, périmètre et norme identifiée. Percentile descriptif croissant, sans recommandation. ROE sur capitaux propres de clôture.'}


def net_return(entry, exit_price, buy_pct, sell_pct, slippage_pct=0):
    if not all(finite(x) for x in (entry, exit_price, buy_pct, sell_pct, slippage_pct)) or entry <= 0:
        raise ValueError('Invalid cost scenario')
    if not 0 <= buy_pct < 100 or not 0 <= sell_pct < 100 or not 0 <= slippage_pct < 100 or sell_pct + slippage_pct >= 100:
        raise ValueError('Invalid cost scenario')
    return 100*(exit_price*(1-(sell_pct+slippage_pct)/100)/(entry*(1+(buy_pct+slippage_pct)/100))-1)


def lab(fixture, history, asof):
    market = calendar(history, asof)
    days, rows, audit = list(market), [], []
    universe = {'MASI': market, **{s: prices(fixture['records'][s], asof) for s in fixture['symbols']}}
    # A single fixed grid shared by every title for each horizon. Intervals
    # [entry, exit] never overlap within a title/horizon. No stock-specific grid.
    for s, p in universe.items():
        rec = fixture['records'].get(s, {})
        boundary = EVENTS.get(s)
        for h in (5, 20, 60):
            counts = {'symbol': s, 'horizon': h, 'candidates': 0, 'observed': 0, 'missing': 0,
                      'event_boundary': 0, 'inactive': 0, 'no_trend': 0}
            for i in range(199, len(days)-h-1, h+1):
                counts['candidates'] += 1
                signal, entry, exit_day = days[i], days[i+1], days[i+1+h]
                window = days[i-49:i+2+h]
                if boundary and window[0] < boundary <= exit_day:
                    counts['event_boundary'] += 1
                    continue
                if rec.get('suspended'):
                    counts['inactive'] += 1
                    continue
                # Reject missing intervening sessions too: no stale fills.
                if any(d not in p for d in window):
                    counts['missing'] += 1
                    continue
                trend = p[signal] > mean(p[d] for d in days[i-19:i+1]) and p[signal] > mean(p[d] for d in days[i-49:i+1])
                if not trend:
                    counts['no_trend'] += 1
                    continue
                counts['observed'] += 1
                rows.append({'symbol': s, 'horizon': h, 'signal_date': signal, 'entry_date': entry,
                             'exit_date': exit_day, 'entry': p[entry], 'exit': p[exit_day],
                             'gross_pct': round(100*(p[exit_day]/p[entry]-1), 6),
                             'masi_pct': round(100*(market[exit_day]/market[entry]-1), 6),
                             'regime': 'above' if market[signal] > mean(market[d] for d in days[i-199:i+1]) else 'below',
                             'period': '2023-2024' if signal < '2025-01-01' else '2025+'})
            audit.append(counts)
    return {'version': VERSION, 'asof': asof, 'masi_first': days[0] if days else None,
            'masi_last': days[-1] if days else None, 'masi_sessions': len(days),
            'universe_size': len(fixture['symbols']), 'rows': rows, 'audit': audit,
            'protocol': 'Clôture > MM20 et MM50 passées. Observation au signal ; entrée au cours de clôture suivant, sortie 5/20/60 séances MASI après entrée. Grille fixe, fenêtres non chevauchantes par titre et horizon. Aucune pondération optimisée.',
            'limitations': ['Étude exploratoire rétrospective, pas un test hors échantillon intact ni un portefeuille exécutable.',
                'Univers actuel : biais de sélection et de survie. Séances absentes, titres suspendus et frontières de capital/reprise exclus, jamais imputés.',
                'Prix seuls, hors dividendes et fiscalité. Archives historiques importées ; ajustements de capital non recertifiés.',
                'Le scénario de frais ne mesure pas les spreads réels ni la capacité d’exécution.',
                'Les fondamentaux actuels ne sont jamais réinjectés dans le passé. Le score canonique ne fait pas partie de ce replay.']}


def enrich(report, fixture):
    history = report.get('masi_history', {})
    for r in report['results']:
        r['market_risk'] = risk(fixture['records'][r['symbol']], history, report['analysis_date'])
    peers(report['results'], fixture['records'])
    report['research'] = lab(fixture, history, report['analysis_date'])


def archive_scores(report, folder, now):
    """First observed daily snapshot, never pretend a current score was known earlier."""
    folder.mkdir(parents=True, exist_ok=True)
    day = now.date().isoformat()
    target = folder / f'{day}.json'
    if report['analysis_date'] == day and not target.exists():
        observations = []
        for r in report['results']:
            inputs = {k: r.get(k) for k in ('price', 'asof', 'quality', 'liquidity', 'technical', 'fundamental')}
            observations.append({'symbol': r['symbol'], 'first_observed_at': now.isoformat(),
                'price_date': r['asof'], 'score': r['canonical_score'], 'inputs': inputs,
                'inputs_sha256': sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()})
        payload = {'version': VERSION, 'first_observed_at': now.isoformat(), 'source_commit': report['source_commit'],
                   'build_commit': report.get('runtime', {}).get('commit'), 'observations': observations}
        # Exclusive create is deliberate; subsequent rebuilds do not rewrite.
        with target.open('x', encoding='utf-8') as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)
    files = sorted(folder.glob('????-??-??.json'))
    return {'daily_snapshots': len(files), 'first_day': files[0].stem if files else None,
            'last_day': files[-1].stem if files else None, 'status': 'collecting',
            'note': 'Première observation quotidienne conservée avec heure, entrées et empreinte. Aucune performance du score encore validée ; les issues seront mesurées après cette observation.'}
