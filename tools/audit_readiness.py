"""Independent arithmetic inventory of published facts; no PDF certification."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def audit(report):
    checks, failures = [], []

    def compare(symbol, metric, actual, expected):
        if actual is None:
            return  # Availability is inventoried separately, never filled here.
        checks.append((symbol, metric))
        if expected is None or abs(Decimal(str(actual)) - expected) > Decimal('0.005001'):
            failures.append(dict(symbol=symbol, metric=metric, actual=actual,
                                 expected=str(expected)))

    rows = report['results']
    for row in rows:
        s, f = row['symbol'], row['fundamental']
        ev = f.get('evidence', {})

        def value(*keys):
            for key in keys:
                e = ev.get(key)
                if e is not None:
                    unit = 'actions' if key.startswith('nombre_actions') else 'MMAD'
                    if key == 'dividende_par_action':
                        unit = 'DH'
                    if e.get('unit') != unit:
                        failures.append(dict(symbol=s, metric='unit:' + key,
                                             actual=e.get('unit'), expected=unit))
                    return Decimal(str(e['value']))
            return None

        net = value('resultat_net_part_groupe', 'resultat_net_social')
        equity = value('capitaux_propres_part_groupe', 'capitaux_propres_sociaux')
        eps_shares = value('nombre_actions_retenu_pour_le_bpa', 'nombre_actions', 'nombre_actions_au_rapport')
        book_shares = value('nombre_actions_existant', 'nombre_actions', 'nombre_actions_au_rapport')
        if f.get('historical_per_share_only'):
            eps_shares = book_shares = value('nombre_actions_annuel_verifie')
        price = Decimal(str(row['price'])) if row.get('price') else None

        def quotient(n, d):
            return n / d if n is not None and d is not None and d > 0 else None

        eps = quotient(net * 1000000 if net is not None else None, eps_shares)
        book = quotient(equity * 1000000 if equity is not None else None, book_shares)
        compare(s, 'eps_mad', f.get('eps_mad'), eps)
        compare(s, 'book_value_per_share_mad', f.get('book_value_per_share_mad'), book)
        compare(s, 'pe', f.get('pe'), quotient(price, eps))
        compare(s, 'pb', f.get('pb'), quotient(price, book))
        compare(s, 'roe_pct', f.get('roe_pct'), quotient(net * 100 if net is not None else None, equity))
        debt, cash, ebe = value('dettes_financieres'), value('tresorerie_actif'), value('excedent_brut_exploitation')
        strict = debt - cash if debt is not None and cash is not None else None
        compare(s, 'net_debt_strict_mmad', f.get('net_debt_strict_mmad'), strict)
        compare(s, 'net_debt_ebitda', f.get('net_debt_ebitda'), quotient(strict, ebe))
        year = f.get('exercise')
        for prefix, metric in [('chiffre_affaires', 'revenue_growth_pct'), ('produit_net_bancaire', 'pnb_growth_pct')]:
            current, previous = value(prefix), value(f'{prefix}_{year-1}') if year else None
            ratio = quotient(current, previous)
            compare(s, metric, f.get(metric), (ratio-1)*100 if ratio is not None else None)
        dividend = value('dividende_par_action')
        compare(s, 'dividend_yield_pct', f.get('dividend_yield_pct'), quotient(dividend*100 if dividend is not None else None, price))
        cs = row.get('canonical_score') or {}
        contributors = list((cs.get('contributors') or {}).values())
        weight = sum(Decimal(str(c['weight'])) for c in contributors)
        points = sum(Decimal(str(c['points'])) for c in contributors)
        compare(s, 'score', cs.get('value'), points / weight * 100 if weight else None)
        if cs.get('nlp_weight') != 0:
            failures.append(dict(symbol=s, metric='nlp_weight', actual=cs.get('nlp_weight'), expected=0))
    metrics = ('eps_mad', 'pe', 'pb', 'roe_pct', 'net_debt_ebitda', 'pnb_mmad')
    return dict(analysis_date=report['analysis_date'], universe=len(rows),
        arithmetic_checks=len(checks), checks_by_metric=dict(Counter(k for _, k in checks)),
        failures=failures, availability={k: sum(r['fundamental'].get(k) is not None for r in rows) for k in metrics},
        annual_validation=dict(Counter(r['fundamental']['validation_status'] for r in rows)),
        price_ages=dict(Counter(str(r.get('age_calendar_days')) for r in rows)),
        score_states=dict(Counter(r['canonical_score']['state'] for r in rows)),
        coverage=report['fundamental_coverage'],
        limitation='Arithmetic of available exported facts only; does not independently verify all PDFs, publication dates, accounting scopes or share denominators.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', nargs='?', default=str(ROOT/'web/report.json'))
    args = parser.parse_args()
    result = audit(json.loads(Path(args.report).read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(bool(result['failures']))
