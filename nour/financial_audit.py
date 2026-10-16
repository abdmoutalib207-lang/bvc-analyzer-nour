"""Deterministic calculation gates over attributed facts; never a financial opinion.

Missing provenance is a review task, not proof of false arithmetic. Explicit
unit/date/scope contradictions withhold affected outputs. This audit does not
scrape reports, invent annual results or certify imported accounting treatments.
"""
from copy import deepcopy
from datetime import date
import math
import re

VERSION = 'nour-financial-audit-v1'
METRICS = ('eps_mad', 'book_value_per_share_mad', 'pe', 'pb', 'roe_pct',
           'roe_average_equity_pct', 'revenue_growth_pct', 'pnb_growth_pct',
           'dividend_yield_pct', 'net_debt_strict_mmad', 'net_debt_ebitda')
# Enumerated statuses already used by Nour; an arbitrary "verified" is not proof.
REVIEWED = frozenset({
    'selected_pages_visually_checked',
    'selected_pages_reconciled_with_reservations_2026-10-05',
    'pdf_page_visually_checked_2026-10-04',
    'historical_closing_shares_visually_checked',
})
HASH = re.compile(r'sha256:[0-9a-f]{64}')


def _finite(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _basis(value):
    """Remove date suffixes only; never equate social, IFRS and national bases."""
    if not isinstance(value, str):
        return ''
    value = re.sub(r'[,;]?\s*(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', '', value)
    return ' '.join(value.casefold().strip(' ,;').split())


def _basis_conflicts(left, right):
    # Free-text labels often include page notes. Only explicit accounting
    # incompatibilities prove a conflict; unequal prose alone does not.
    def tags(value):
        value = _basis(value)
        scope = ('consolidated' if 'consolid' in value else
                 'social' if ('social' in value or 'sociaux' in value) else None)
        standard = ('ifrs' if 'ifrs' in value else
                    'national' if ('normes marocaines' in value or 'normes nationales' in value) else None)
        return scope, standard
    a, b = tags(left), tags(right)
    return any(x is not None and y is not None and x != y for x, y in zip(a, b))


def _usable(item):
    return (isinstance(item, dict) and _finite(item.get('valeur'))
            and isinstance(item.get('page'), int) and not isinstance(item['page'], bool)
            and item['page'] > 0 and item.get('devise', 'MAD') == 'MAD')


def audit_financials(record, facts, asof, calculated=None):
    """Return JSON-safe checks/blocked_metrics for one issuer at an explicit date.

    `calculated` may be fundamentals.calculate's output; only its successfully
    reconciled debt bridge status is consulted. No input is mutated.
    """
    on = _day(asof)
    if on is None:
        raise ValueError('asof doit être une date ISO explicite')
    f = facts if isinstance(facts, dict) else {}
    data = f.get('faits') or {}
    checks, blocked = [], set()

    def add(code, status, fields=(), metrics=(), detail=None):
        checks.append(dict(code=code, status=status, fields=list(fields),
                           blocked_metrics=list(metrics), detail=detail))
        if status == 'blocked':
            blocked.update(metrics)

    year = f.get('exercice')
    annual = f.get('exercice_clos') or (f'{year}-12-31' if isinstance(year, int) and not isinstance(year, bool) else None)
    annual_day = _day(annual)
    latest = f.get('latest_report') or {}
    latest_day = _day(latest.get('period_end'))
    freshness = dict(annual_period_end=annual, latest_report_period_end=latest.get('period_end'),
                     newer_report_available=bool(annual_day and latest_day and latest_day > annual_day),
                     annual_age_calendar_days=(on - annual_day).days if annual_day else None,
                     annual_years_behind_latest=(latest_day.year - annual_day.year) if annual_day and latest_day else None,
                     semester_annualized=False)
    if not f:
        add('annual_facts_missing', 'review_required')
    elif annual_day is None:
        add('annual_period_invalid', 'blocked', metrics=METRICS)
    elif annual_day > on:
        add('annual_period_future', 'blocked', metrics=METRICS)
    if f.get('devise', 'MAD') != 'MAD':
        add('currency_conversion_not_documented', 'blocked', metrics=METRICS)
    if freshness['newer_report_available']:
        add('newer_report_available', 'info', detail='Ratios annuels conservés ; référence plus récente distincte, jamais annualisée.')
        if latest_day.year - annual_day.year > 1:
            add('annual_reference_older_than_latest_year', 'review_required',
                detail='Rechercher le rapport annuel intermédiaire ; ne pas le reconstituer à partir du semestre.')
    if latest_day and latest_day > on:
        add('latest_report_period_future', 'review_required')

    def select(*keys):
        # Follow calculate's numeric/page fallback, but preserve invalid-only
        # inputs for diagnosis instead of silently accepting them.
        return next((k for k in keys if _usable(data.get(k))),
                    next((k for k in keys if data.get(k)), keys[0]))

    net = select('resultat_net_part_groupe', 'resultat_net_social')
    equity = select('capitaux_propres_part_groupe', 'capitaux_propres_sociaux')
    ordinary = select('nombre_actions', 'nombre_actions_au_rapport')
    eps_shares = select('nombre_actions_retenu_pour_le_bpa', ordinary)
    book_shares = select('nombre_actions_existant', ordinary)
    if f.get('capital_change_unresolved'):
        # calculate already validates the historical-only denominator contract.
        eps_shares = book_shares = 'nombre_actions_annuel_verifie'
    previous_revenue = f'chiffre_affaires_{year - 1}' if isinstance(year, int) and not isinstance(year, bool) else 'chiffre_affaires_precedent'
    previous_pnb = f'produit_net_bancaire_{year - 1}' if isinstance(year, int) and not isinstance(year, bool) else 'produit_net_bancaire_precedent'
    deps = {
        'eps_mad': [net, eps_shares], 'pe': [net, eps_shares],
        'book_value_per_share_mad': [equity, book_shares], 'pb': [equity, book_shares],
        'roe_pct': [net, equity], 'roe_average_equity_pct': [net, equity],
        'revenue_growth_pct': ['chiffre_affaires', previous_revenue],
        'pnb_growth_pct': ['produit_net_bancaire', previous_pnb],
        'dividend_yield_pct': ['dividende_par_action'],
        'net_debt_strict_mmad': ['dettes_financieres', 'tresorerie_actif'],
        'net_debt_ebitda': ['dettes_financieres', 'tresorerie_actif', 'excedent_brut_exploitation'],
    }
    positive = {eps_shares, book_shares, equity, previous_revenue, previous_pnb,
                'excedent_brut_exploitation'}
    pending = set()
    for key in sorted({k for keys in deps.values() for k in keys}):
        item = data.get(key)
        affected = [metric for metric, keys in deps.items() if key in keys]
        if not isinstance(item, dict):
            # Missing output is already withheld by calculate; keep one compact
            # group below rather than issuing dozens of absent-field warnings.
            continue
        if not _usable(item):
            add('invalid_numeric_fact', 'blocked', [key], affected)
            continue
        unit = 'actions' if key.startswith('nombre_actions') else 'MAD' if key == 'dividende_par_action' else 'MMAD'
        if item.get('unite') is not None and item['unite'] not in ({'MAD', 'DH'} if key == 'dividende_par_action' else {unit}):
            add('fact_unit_mismatch', 'blocked', [key], affected, f'Unité attendue : {unit}')
        if unit == 'actions' and (item['valeur'] <= 0 or not float(item['valeur']).is_integer()):
            add('share_denominator_invalid', 'blocked', [key], affected)
        if key in ('dettes_financieres', 'tresorerie_actif', 'dividende_par_action') and item['valeur'] < 0:
            add('negative_asset_debt_or_dividend', 'blocked', [key], affected)
        if key in positive and item['valeur'] <= 0:
            add('nonpositive_denominator', 'blocked', [key],
                [m for m in affected if m != 'book_value_per_share_mad'] if key == equity else affected)
        expected = f'{year - 1}{annual[4:]}' if key in (previous_revenue, previous_pnb) and annual_day else annual
        explicit = item.get('period_end')
        if explicit is not None and (_day(explicit) is None or explicit != expected):
            add('fact_period_mismatch', 'blocked', [key], affected,
                f'Période attendue {expected}, relevée {explicit}')
        if (not HASH.fullmatch(str(item.get('document_hash', '')))
                or item.get('validation_status') not in REVIEWED
                or not str(item.get('url') or '').startswith('https://')
                or item.get('unite') is None or explicit is None or not item.get('base')):
            pending.add(key)
    if pending:
        add('fact_provenance_incomplete', 'review_required', sorted(pending),
            detail='Pages, empreintes, unités, dates et périmètres à compléter ; une importation référencée ne vaut pas vérification indépendante.')
    if not data.get(net) and data.get('resultat_net_consolide'):
        add('group_earnings_missing_total_not_substituted', 'blocked',
            ['resultat_net_consolide'], ['eps_mad', 'pe', 'roe_pct', 'roe_average_equity_pct'])
    if _usable(data.get(net)) and data[net]['valeur'] <= 0:
        add('nonpositive_earnings_per_not_meaningful', 'blocked', [net], ['pe'],
            'Perte ou résultat nul observé : BPA conservé, PER positif indisponible.')
    if (net.endswith('part_groupe') and equity.endswith('sociaux')) or (net.endswith('social') and equity.endswith('part_groupe')):
        if data.get(net) and data.get(equity):
            add('earnings_equity_scope_mismatch', 'blocked', [net, equity], ['roe_pct', 'roe_average_equity_pct'])
    for metric, keys in deps.items():
        if metric == 'dividend_yield_pct':
            continue
        bases = {_basis(data[k].get('base')) for k in keys if isinstance(data.get(k), dict) and data[k].get('base')}
        if any(_basis_conflicts(left, right) for left in bases for right in bases):
            add('calculation_basis_mismatch', 'blocked', keys, [metric])

    comparison = dict(status='not_available', calculated_mmad=None, reported_mmad=None,
                      difference_mmad=None, tolerance_mmad=None)
    core = ['dettes_financieres', 'tresorerie_actif', 'endettement_net']
    if f.get('financial_business'):
        comparison['status'] = 'not_applicable'
    elif all(_usable(data.get(k)) for k in core):
        rows = [data[k] for k in core]
        bases = {_basis(row.get('base')) for row in rows}
        compatible = (len(bases) == 1 and '' not in bases
                      and all(row.get('period_end') == annual and row.get('unite') == 'MMAD' for row in rows))
        if compatible:
            strict = rows[0]['valeur'] - rows[1]['valeur']
            reported = rows[2]['valeur']
            tolerance = max(1., .02 * abs(reported))
            gap = strict - reported
            if all(_finite(v) for v in (strict, reported, gap, tolerance)):
                comparison.update(status='within_tolerance' if abs(gap) <= tolerance else 'unresolved',
                                  calculated_mmad=round(strict, 6), reported_mmad=reported,
                                  difference_mmad=round(gap, 6), tolerance_mmad=tolerance)
                if (calculated or {}).get('debt_reconciliation', {}).get('status') == 'scope_reconciled':
                    comparison['status'] = 'scope_reconciled'
                elif abs(gap) > tolerance:
                    add('debt_arithmetic_mismatch', 'blocked', core,
                        ['net_debt_strict_mmad', 'net_debt_ebitda'],
                        'Écart à date, unité et base comptable identiques ; définition économique de dette à rapprocher, sans arbitrage automatique.')
            else:
                add('debt_arithmetic_nonfinite', 'blocked', core,
                    ['net_debt_strict_mmad', 'net_debt_ebitda'])
        else:
            comparison['status'] = 'not_comparable'
            add('published_debt_basis_not_comparable', 'review_required', core,
                detail='Pas de conclusion de contradiction sans date, unité et périmètre explicites identiques.')
    return dict(version=VERSION, asof=asof, symbol=record.get('symbol'),
                scope='available_annual_inputs_only', documents_certified=False,
                status='blocked' if blocked else 'review_required' if any(c['status'] == 'review_required' for c in checks) else 'checked',
                blocked_metrics=sorted(blocked), checks=checks, freshness=freshness,
                debt_comparison=comparison, automatic_extraction_certified=False)


def apply_financial_audit(calculated, audit):
    """Copy, withhold unsafe metrics and recalculate coverage; never alter facts."""
    out = deepcopy(calculated)
    for key in audit['blocked_metrics']:
        if key in METRICS:
            out[key] = None
    metrics = ('eps_mad', 'pb', 'roe_pct', 'revenue_growth_pct')
    out['coverage_pct'] = 25 * sum(out.get(k) is not None for k in metrics)
    out['missing_metrics'] = [k for k in metrics if out.get(k) is None]
    out['financial_audit'] = deepcopy(audit)
    return out


def audit_dataset(facts_by_symbol, market_by_symbol, asof):
    """Compact inventory usable by build/CI; caller owns persistence and policy."""
    if _day(asof) is None:
        raise ValueError('asof doit être une date ISO explicite')
    issuers = {symbol: audit_financials(dict(market_by_symbol.get(symbol) or {}, symbol=symbol), facts, asof)
               for symbol, facts in sorted(facts_by_symbol.items())}
    return dict(version=VERSION, asof=asof, issuers=issuers,
                summary=dict(issuers=len(issuers),
                             blocked=sum(a['status'] == 'blocked' for a in issuers.values()),
                             review_required=sum(a['status'] == 'review_required' for a in issuers.values()),
                             checked=sum(a['status'] == 'checked' for a in issuers.values())))
