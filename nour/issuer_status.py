"""Dated documentary status, separate from financial facts and trading scores."""
from copy import deepcopy


def apply_status(fixture, registry, asof):
    """Use an explicit dated registry; never infer delisting from missing quotes."""
    result = deepcopy(fixture)
    observed = registry.get('observed_asof')
    if not isinstance(observed, str) or observed > asof:
        return result
    for symbol, entry in registry.get('records', {}).items():
        record = result['records'].get(symbol)
        if record is None:
            continue
        record['issuer_status'] = {**deepcopy(entry), 'observed_asof': observed,
            'source_commit': registry.get('source_commit'),
            'validation': 'Statut documentaire rapproché du moteur principal et du catalogue officiel ; pas de certification des comptes.'}
        if entry.get('trading_status') == 'suspended':
            if record.get('price') is not None:
                record['reference_quote'] = {'price': record['price'], 'date': None,
                    'notice': 'Référence ancienne rediffusée ; aucune clôture récente attestée.'}
            record.update(suspended=True, stale=True, price=None, price_asof=None)
    return result
