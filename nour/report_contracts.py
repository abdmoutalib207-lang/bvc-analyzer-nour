"""Publish one dated market view; retain the initial legacy block only as archival."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation


def volume_reconciliation(report, overview):
    """Compare actual turnover for the same session, without changing either source."""
    def number(value):
        try:
            result = Decimal(str(value))
            return result if result.is_finite() and result >= 0 else None
        except InvalidOperation:
            return None

    total = number(overview.get('turnover_mad'))
    expected = number((overview.get('breadth') or {}).get('quoted'))
    rows = [r for r in report.get('results', [])
            if overview.get('asof') and r.get('asof') == overview['asof']
            and ((number(r.get('day_shares')) or 0) > 0
                 or (number(r.get('day_turnover_mad_actual')) or 0) > 0)]
    amounts = [number(r.get('day_turnover_mad_actual')) for r in rows]
    complete = bool(expected and expected == len(rows)
                    and all(v is not None for v in amounts)
                    and len({r.get('symbol') for r in rows if r.get('symbol')}) == len(rows))
    line_total = sum((v for v in amounts if v is not None), Decimal(0)) if rows else None
    delta = line_total - total if line_total is not None and total is not None else None
    status = ('unavailable' if total is None else 'incomplete' if not complete
              else 'matched' if abs(delta) <= Decimal('.01') else 'discrepancy')
    return dict(status=status, asof=overview.get('asof'), observed_at=overview.get('observed_at'),
                expected_lines=int(expected) if expected is not None else None,
                observed_lines=len(rows), coverage_complete=complete,
                cdg_turnover_mad=float(total) if total is not None else None,
                lines_turnover_mad=float(line_total) if line_total is not None else None,
                difference_mad=float(delta) if delta is not None else None)


def synchronize_market(report, overview):
    current = deepcopy(overview or {})
    if current.get('asof') and report.get('analysis_date') and current['asof'] > report['analysis_date']:
        current = {'status': 'unavailable', 'note': 'Vue de marché future exclue à la date d’analyse.'}
    report['market_overview'] = current
    report['market_volume_audit'] = volume_reconciliation(report, current)
    report['market_archive'] = deepcopy(report.get('market_archive') or report.get('market') or {})
    report['market'] = dict(last_session=current.get('asof'), status=current.get('status','unavailable'),
        masi=deepcopy(current.get('masi') or {}), source=current.get('source'),
        observed_at=current.get('observed_at'), turnover_mad=current.get('turnover_mad'),
        breadth=deepcopy(current.get('breadth') or {}))
    return report
