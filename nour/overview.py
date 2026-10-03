"""Dated index observations, kept separate from final daily closes and scores."""
import copy
import json
from datetime import datetime
from urllib.request import Request, urlopen

from .market import CASABLANCA, CANCELLED_SESSIONS, SOURCE_URL, numeric, session_date

SECTORS = ('BANK', 'B&MC', 'IMMOB', 'SPI', 'ASSUR', 'MINES', 'TCOM',
           'AGRO', 'P&G', 'DISTR', 'L&SI', 'SDT', 'PHARM', 'I&BEI',
           'CHIM', 'ELEC', 'SF&AF', 'SP&H', 'TRANS', 'SANTE', 'L&H', 'BOISS', 'S&P')


def fetch_indices(timeout=30):
    actions = []
    for code in ('MASI', *SECTORS):
        params = [('Lang_', 'S', 'fr'), ('Espace_', 'I', '1'),
                  ('IdPartener_', 'I', '1'), ('Indice_', 'S', code)]
        actions.append({'ACTION': {'NAME': 'INDICE-SYNTHESE', 'TYPE': 'SELECT',
                                   'VALUE': 'INDICE-SYNTHESE'},
                        'PARAMS': [dict(NAME=n, TYPE=t, VALUE=v) for n,t,v in params]})
    req = Request(SOURCE_URL, data=json.dumps({'ACTIONS': actions}).encode(),
                  headers={'Content-Type': 'application/json',
                           'User-Agent': 'BVCAnalyzerNour/1.0 (+public research)',
                           'Referer': 'https://www.cdgcapitalbourse.ma/Bourse/market'})
    with urlopen(req, timeout=timeout) as response:
        payload = json.load(response)
    rows = []
    for code, block in zip(('MASI', *SECTORS), payload):
        value = block.get('INDICE-SYNTHESE', {})
        data = value.get('Data') or []
        if value.get('Valid') is True and data and data[0].get('Symbol') == code:
            rows.append(data[0])
    return rows


def update_overview(previous, history, indices, quotes, now=None):
    now = (now or datetime.now(CASABLANCA)).astimezone(CASABLANCA)
    today = now.date().isoformat()
    row = next((r for r in indices if r.get('Symbol') == 'MASI'), None)
    if row is None:
        raise ValueError('MASI absent de la réponse CDG')
    day = session_date(row.get('DateCotation'))
    value, reference = numeric(row.get('Cours')), numeric(row.get('CoursVeille'))
    if not day or day > today or day in CANCELLED_SESSIONS or value is None or value <= 0:
        raise ValueError('MASI sans date ou valeur admissible')
    if previous.get('current', {}).get('asof', '') > day:
        raise ValueError('Recul de la date MASI refusé')
    provisional = day == today and now.hour < 16
    snapshot = {'schema_version': 1, 'asof': day, 'observed_at': now.isoformat(),
                'status': 'intraday' if provisional else 'closed',
                'source': 'CDG Capital Bourse',
                'source_url': 'https://www.cdgcapitalbourse.ma/Bourse/market',
                'masi': {'value': value, 'asof': day, 'veille': reference,
                         'change_pct': round((value/reference-1)*100, 2) if reference and reference > 0 else None,
                         'variation_points': round(value-reference, 2) if reference else None},
                'high': numeric(row.get('PlusHaut')), 'low': numeric(row.get('PlusBas')),
                'sectors': []}
    breadth = {out: numeric(row.get(field)) for out,field in (
        ('up','NbrHausse'), ('down','NbrBaisse'), ('flat','NbrInchange'), ('quoted','NbrValeur'))}
    if (all(v is not None and v >= 0 and v.is_integer() for v in breadth.values())
            and sum(breadth[k] for k in ('up','down','flat')) == breadth['quoted']):
        snapshot['breadth'] = {k:int(v) for k,v in breadth.items()}
    for output, field in (('turnover_mad','Volume'), ('shares','QteEchange'),
                          ('transactions','NbrTransaction')):
        value_field = numeric(row.get(field))
        if value_field is not None and value_field >= 0:
            snapshot[output] = value_field
    for r in indices:
        if r.get('Symbol') in SECTORS and session_date(r.get('DateCotation')) == day:
            change = numeric(r.get('VariationP'))
            if change is not None and r.get('Libelle'):
                snapshot['sectors'].append({'code': r['Symbol'], 'libelle': r['Libelle'],
                                            'variation_pct': change})
    snapshot['sectors'].sort(key=lambda r: -r['variation_pct'])
    # Aggregate only dated traded lines. This is CDG coverage, not the number
    # of histories that happen to pass Nour's stricter OHLC validation.
    fresh = [r for r in quotes if session_date(r.get('DateDernierCours')) == day
             and (numeric(r.get('QteEchangee')) or 0) > 0]
    symbols = [r.get('Symbol') for r in fresh]
    if len(set(symbols)) != len(symbols):
        raise ValueError('Lignes de séance dupliquées')
    if len(fresh) >= 20:
        changes = [numeric(r.get('VariationP')) for r in fresh]
        if 'breadth' not in snapshot and all(c is not None for c in changes):
            snapshot['breadth'] = {'up': sum(c > 0 for c in changes),
                                   'down': sum(c < 0 for c in changes),
                                   'flat': sum(c == 0 for c in changes), 'quoted': len(fresh)}
        for output, field in (('turnover_mad', 'Volumes'), ('shares', 'QteEchangee')):
            values = [numeric(r.get(field)) for r in fresh]
            if output not in snapshot and all(v is not None and v >= 0 for v in values):
                snapshot[output] = sum(values)
    updated, series = copy.deepcopy(previous), copy.deepcopy(history)
    closes = series.setdefault('seances', {})
    if not provisional:
        existing = closes.get(day)
        if existing is not None and abs(existing-value) > .01:
            raise ValueError('Clôture historique MASI divergente : correction explicite nécessaire')
        closes[day] = value
        updated['last_closed'] = copy.deepcopy(snapshot)
    anchors = [d for d in closes if d[:4] < day[:4]]
    if anchors:
        snapshot['masi']['ytd_pct'] = round((value/closes[max(anchors)]-1)*100, 2)
        if not provisional:
            updated['last_closed']['masi']['ytd_pct'] = snapshot['masi']['ytd_pct']
    updated['current'] = snapshot
    series['seances'] = dict(sorted(closes.items()))
    return updated, series
