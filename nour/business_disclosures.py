"""Reviewed issuer disclosures, with physical dimensions and signed cash flows.

This catalogue is independent of score inputs. No aggregation, currency
conversion, annualisation, or reinterpretation of a concentrate is performed.
"""
from copy import deepcopy
from datetime import date
import json
import math
import re
from urllib.parse import urlsplit

VERSION = 'nour-business-disclosures-v1'
CATEGORIES = {'production', 'expenses', 'investments', 'cash_flows', 'activity', 'backlog', 'unit_cost'}
OFFICIAL_HOSTS = {'www.managemgroup.com', 'managemgroup.com', 'www.ammc.ma', 'ammc.ma', 'www.marsamaroc.co.ma', 'marsamaroc.co.ma', 'tgcc.ma', 'www.tgcc.ma'}


def load_catalogue(directory):
    return {path.stem: json.loads(path.read_text(encoding='utf-8'))
            for path in sorted(directory.glob('*.json'))} if directory.exists() else {}


def disclosure_view(catalogue, asof):
    """Fail closed on malformed evidence; keep a reason instead of a false zero."""
    if not catalogue:
        return {'version': VERSION, 'records': [], 'reservations': [], 'used_for_score': False}
    try:
        available = date.fromisoformat(catalogue['available_from'])
        reviewed = date.fromisoformat(catalogue['reviewed_on'])
        current = date.fromisoformat(asof)
        valid = (catalogue['schema_version'] == VERSION
                 and catalogue['validation_status'] in ('selected_pages_visually_checked', 'automatic_text_extraction')
                 and reviewed <= available <= current)
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        return {'version': VERSION, 'records': [], 'reservations': [
            'Relevé métier indisponible à cette date ou revue documentaire non vérifiée.'],
            'used_for_score': False}
    records = []
    seen = set()
    for raw in catalogue.get('records', []):
        if not isinstance(raw, dict):
            continue
        row = deepcopy(raw)
        source = catalogue.get('documents', {}).get(row.get('document'), {})
        reason = None
        try:
            start, end = date.fromisoformat(row['period_start']), date.fromisoformat(row['period_end'])
            unit = row['unit']
            physical = row['category'] == 'production'
            url = urlsplit(source.get('url', ''))
            ok = (isinstance(row['id'], str) and row['id'] not in seen and bool(row['label']) and bool(row['scope'])
                  and bool(row['definition']) and row['category'] in CATEGORIES
                  and start <= end <= current and date.fromisoformat(row.get('available_from',catalogue['available_from']))<=current
                  and ((row['period_kind'] == 'annual' and start.month == 1 and start.day == 1
                        and end.month == 12 and end.day == 31 and start.year == end.year)
                       or (row['period_kind'] == 'semester' and start.month == 1 and start.day == 1
                           and end.month == 6 and end.day == 30 and start.year == end.year))
                  and isinstance(row['value'], (int, float)) and not isinstance(row['value'], bool)
                  and math.isfinite(row['value'])
                  and isinstance(row['page'], int) and not isinstance(row['page'], bool) and row['page'] > 0
                  and bool(row.get('printed_page')) and bool(source.get('title'))
                  and re.fullmatch(r'sha256:[0-9a-f]{64}', source.get('document_hash', ''))
                  and url.scheme == 'https' and url.hostname in OFFICIAL_HOSTS
                  and not url.username and not url.password
                  and ((physical and unit in ('TC', 'kg', 'TM') and row['value'] >= 0
                        and bool(row.get('metal')) and row.get('quantity_basis') ==
                        ('concentrate' if unit == 'TC' else 'published_metal'))
                       or (not physical and unit == 'MDH' and row.get('currency') == 'MAD')
                       or (row['category']=='activity' and unit in ('millions de tonnes','EVP','t','g Ag/t','%') and row['value']>=0)
                       or (row['category']=='unit_cost' and unit=='USD/oz' and row.get('currency')=='USD' and row.get('metal') and row['value']>=0)))
            if not ok:
                reason = 'Valeur, unité, période, périmètre ou preuve primaire non vérifiée.'
        except (KeyError, TypeError, ValueError, OverflowError):
            reason = 'Valeur, unité, période, périmètre ou preuve primaire non vérifiée.'
        if isinstance(row.get('id'), str):
            seen.add(row['id'])
        extraction = catalogue['validation_status']=='automatic_text_extraction' and source.get('review_status')!='selected_pages_visually_checked'
        row.update(source=deepcopy(source), status=('automatic_text_extracted' if extraction else 'primary_page_checked') if reason is None else 'unavailable',
                   reason=reason, value=row.get('value') if reason is None else None,
                   used_for_score=False, certified=False)
        records.append(row)
    return {'version': VERSION, 'records': records, 'reservations': deepcopy(catalogue.get('reservations', [])),
            'reviewed_on': catalogue['reviewed_on'], 'available_from': catalogue['available_from'],
            'collection_status':catalogue.get('collection_status'),
            'used_for_score': False, 'certified': False}


def attach_business_facts(facts, catalogues, asof):
    """Add reviewed supplemental facts; never overwrite the core financial facts."""
    out = deepcopy(facts)
    for symbol, catalogue in catalogues.items():
        if symbol not in out or catalogue.get('symbol') != symbol:
            raise ValueError('Identité du relevé métier non rapprochée')
        record = out[symbol]
        record['business_disclosures'] = deepcopy(catalogue)
        view = disclosure_view(catalogue, asof)
        # A single annual TFT acquisition line may supply positive cash CAPEX.
        # Keep the original signed line and its exact document/page alongside it.
        period = record.get('exercice_clos') or f"{record.get('exercice')}-12-31"
        candidates = [r for r in view['records'] if r.get('id') == f'cash-capex-{record.get("exercice")}'
                      and r['status'] == 'primary_page_checked' and r['category'] == 'cash_flows'
                      and r['period_kind'] == 'annual' and r['period_end'] == period
                      and r['scope'] == 'Groupe consolidé IFRS' and r['value'] <= 0]
        if len(candidates) == 1:
            row = candidates[0]
            supplemental = record.setdefault('sector_faits', {})
            if 'capex_decaisse' not in supplemental:
                supplemental['capex_decaisse'] = dict(valeur=-row['value'], unite='MMAD', devise='MAD',
                    valeur_au_rapport=row['value'], unite_au_rapport='MDH',
                    normalization='cash_outflow_to_positive_capex', base='consolidé IFRS',
                    period_end=period, page=row['page'], printed_page=row['printed_page'],
                    url=row['source']['url'], document_hash=row['source']['document_hash'],
                    validation_status='selected_pages_visually_checked',
                    note='Ligne du tableau de trésorerie, arrondie au million dans le document. Signe inversé pour le ratio CAPEX ; distinct des investissements de gestion.')
    return out
