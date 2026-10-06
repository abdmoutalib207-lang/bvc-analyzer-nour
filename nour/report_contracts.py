"""Publish one dated market view; retain the initial legacy block only as archival."""
from copy import deepcopy


def synchronize_market(report, overview):
    current = deepcopy(overview or {})
    if current.get('asof') and report.get('analysis_date') and current['asof'] > report['analysis_date']:
        current = {'status': 'unavailable', 'note': 'Vue de marché future exclue à la date d’analyse.'}
    report['market_overview'] = current
    report['market_archive'] = deepcopy(report.get('market_archive') or report.get('market') or {})
    report['market'] = dict(last_session=current.get('asof'), status=current.get('status','unavailable'),
        masi=deepcopy(current.get('masi') or {}), source=current.get('source'),
        observed_at=current.get('observed_at'), turnover_mad=current.get('turnover_mad'),
        breadth=deepcopy(current.get('breadth') or {}))
    return report
