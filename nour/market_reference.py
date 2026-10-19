"""Field-level market provenance; a dated index never dates every counter."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import urlsplit


def reviewed_reference(overview, reference):
    """Accept only a same-session, explicitly reviewed official capture.

    This is a human-reviewed documentary reference, not a live official feed.
    Matching aggregate figures never attest the equity-only decomposition.
    """
    try:
        if reference.get('schema_version') != 1:
            return None
        session=overview['asof'];date.fromisoformat(session)
        entry=reference['sessions'][session]
        if entry['asof']!=session or entry['review_status']!='manual_capture_reviewed':
            return None
        source=urlsplit(entry['source_url'])
        if (source.scheme!='https' or source.hostname!='www.casablanca-bourse.com'
                or source.path!='/market-data/volume' or source.username or source.password
                or source.query or source.fragment):
            return None
        if not re.fullmatch(r'[0-9a-f]{64}',entry['capture_sha256']):
            return None
        stamp=datetime.fromisoformat(entry['reviewed_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None or stamp.date()<date.fromisoformat(session):
            return None
        for key in ('turnover_mad','shares','contracts'):
            if isinstance(entry[key],bool):
                return None
            value=Decimal(str(entry[key]))
            if not value.is_finite() or value<0 or key!='turnover_mad' and value!=value.to_integral_value():
                return None
        if type(entry['shares']) is not int or type(entry['contracts']) is not int:
            return None
        for key in ('turnover_mad','shares'):
            if isinstance(overview[key],bool) or Decimal(str(entry[key]))!=Decimal(str(overview[key])):
                return None
        return deepcopy(entry)
    except (KeyError,TypeError,ValueError,InvalidOperation):
        return None


def apply_market_reference(overview, reference):
    result=deepcopy(overview or {})
    # Keep the original observation, without assigning it the index's date.
    reported=result.get('transactions_reported') if result.get('transactions_quality') else result.get('transactions')
    result['transactions_reported']=reported
    result['transactions']=None
    result['transactions_quality']={
        'status':'session_not_independently_attested',
        'source_url':result.get('source_url'),
        'notice':'Compteur fournisseur conservé ; sa date propre n’est pas attestée par la date du MASI. Aucun rattachement à une autre séance n’est déduit.'}
    result.pop('official_reference',None)
    checked=reviewed_reference(result,reference or {})
    if checked:
        result['official_reference']=checked
    return result
