"""Read-only comparison with a secondary screener, never financial certification.

Only JSON data are decoded; JavaScript is never executed. The fixed source is
not an official publication. Document labels/pages are leads for primary review.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
import base64
import hashlib
import json
import math
import re
import unicodedata
import zlib

from .official_sources import fetch

SOURCE_URL = 'https://ms-screener.vercel.app/app.js'
ORIGINS = frozenset({'https://ms-screener.vercel.app'})
MAX_SCRIPT = 3_000_000
MAX_JSON = 16_000_000
VERSION = 'nour-screener-reconciliation-v1'
STATUSES = ('agreement', 'rounding', 'difference', 'not_comparable', 'missing')
# Names observed and manually reviewed on 2026-11-09; the existing source-code
# registry selects the issuer first (SNA is not the same issuer in both systems).
# A changed name requires review; neither name nor ticker certifies an ISIN.
REVIEWED_SOURCE_NAMES = {'ADH': 'Douja Prom Addoha',
 'ADI': 'Alliances',
 'AFI': 'Afric Industries SA',
 'AFM': 'Afma',
 'AGM': 'Agma',
 'AKT': 'Akdital',
 'ALM': 'Aluminium du Maroc',
 'ARD': 'Aradei Capital',
 'ATH': 'Auto Hall',
 'ATL': 'AtlantaSanad',
 'ATW': 'Attijariwafa Bank',
 'BAL': 'Balima',
 'BCI': 'BMCI',
 'BCP': 'Banque Centrale Populaire',
 'BOA': 'Bank of Africa (BMCE)',
 'CAP': 'Cash Plus SA',
 'CDM': 'Crédit du Maroc',
 'CFG': 'CFG Bank',
 'CIH': 'CIH Bank',
 'CMA': 'Ciments du Maroc',
 'CMG': 'CMGP Group',
 'CMT': 'Compagnie Minière de Touissit',
 'COL': 'Colorado',
 'CRS': 'Cartier Saada',
 'CSR': 'Cosumar',
 'CTM': 'CTM',
 'DHO': 'Delta Holding',
 'DRI': 'Dari Couspate',
 'DWY': 'Disway',
 'DYT': 'Disty Technologies',
 'EQD': 'Eqdom',
 'FBR': 'Fenie Brossette',
 'GAZ': 'Afriquia Gaz',
 'GTM': 'SGTM S.A.',
 'HPS': 'HPS',
 'IAM': 'Itissalat Al-Maghrib (IAM)',
 'IBC': 'IB Maroc.com',
 'IMO': 'Immorente Invest',
 'INV': 'Involys',
 'JET': 'Jet Contractors',
 'LBV': 'Label Vie',
 'LES': 'Lesieur Cristal',
 'LHM': 'LafargeHolcim Maroc',
 'M2M': 'M2M Group',
 'MAB': 'Maghrebail',
 'MDP': 'Med Paper',
 'MIC': 'Microdata',
 'MLE': 'Maroc Leasing',
 'MNG': 'Managem',
 'MOX': 'Maghreb Oxygène',
 'MSA': 'SODEP-Marsa Maroc',
 'MUT': 'Mutandis SCA',
 'NEJ': 'Auto Nejma',
 'NKL': 'Ennakl Automobiles',
 'OUL': 'Oulmès',
 'PRO': 'Promopharm S.A.',
 'RDS': 'Résidences Dar Saada',
 'REB': 'Rebab Company',
 'RIS': 'Risma',
 'S2M': 'S.M Monétique',
 'SAH': 'Sanlam Maroc',
 'SBM': 'Société des Boissons du Maroc',
 'SID': 'Sonasid',
 'SLF': 'Salafin',
 'SMI': 'SMI',
 'SNA': 'Stokvis Nord Afrique',
 'SNP': 'SNEP',
 'SOT': 'Sothema',
 'SRM': 'Réalisations Mécaniques',
 'STR': 'Stroc Industrie',
 'T2S': 'T2S (introduction 2026)',
 'TGC': 'TGCC S.A.',
 'TMA': 'TotalEnergies Marketing Maroc',
 'TQM': 'Taqa Morocco',
 'UMR': 'Unimer',
 'VCN': 'Vicenne',
 'WAA': 'Wafa Assurance',
 'ZDJ': 'Zellidja S.A.'}
# Exact economic identities; no RN total -> RNPG or CA -> PNB substitution.
FIELDS = {
    'chiffre_affaires': ('CA', 'MMAD'),
    'produit_net_bancaire': ('PNB', 'MMAD'),
    'resultat_net_part_groupe': ('RNPG', 'MMAD'),
    'resultat_net_social': ('RNPG', 'MMAD'),
    'resultat_net_consolide': ('resultat_net_total', 'MMAD'),
    'capitaux_propres_part_groupe': ('capitaux_propres_groupe', 'MMAD'),
    'capitaux_propres_sociaux': ('capitaux_propres', 'MMAD'),
    'capitaux_propres_consolides': ('capitaux_propres', 'MMAD'),
    'resultat_exploitation': ('REX', 'MMAD'),
    'resultat_financier': ('charges_fin_nettes', 'MMAD'),
    'excedent_brut_exploitation': ('EBE', 'MMAD'),
    'dettes_financieres': ('dette_financiere', 'MMAD'),
    'endettement_net': ('dette_nette', 'MMAD'),
    'tresorerie_actif': ('tresorerie', 'MMAD'),
    'total_actif': ('total_actif', 'MMAD'),
    'nombre_actions': ('nb_titres', 'actions'),
    'dividende_par_action': ('dpa_propose', 'MAD'),
}


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _plain(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold()) if not unicodedata.combining(c))


def scope(value):
    value = _plain(value)
    if 'consolid' in value:
        return 'consolidated'
    if 'social' in value or 'sociaux' in value:
        return 'social'
    return None


def standard(value):
    value = _plain(value)
    if 'ifrs' in value or re.search(r'\bias\b', value):
        return 'ifrs'
    if any(k in value for k in ('cnc', 'pcgi', 'cgnc', 'pcec', 'marocain', 'national')):
        return 'national'
    return None


def clock(value=None):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    dt = dt or datetime.now(timezone.utc)
    if not isinstance(dt, datetime) or dt.utcoffset() is None:
        raise ValueError('explicit_timezone_required')
    return dt.isoformat()


def decode_script(script):
    if not isinstance(script, bytes) or len(script) > MAX_SCRIPT:
        raise ValueError('script_size_or_type')
    found = re.findall(rb'atob\(\s*[\'"]([A-Za-z0-9+/=]+)[\'"]\s*\)', script)
    if len(found) != 1:
        raise ValueError('embedded_payload_ambiguous_or_absent')
    raw = base64.b64decode(found[0], validate=True)
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decoded = decoder.decompress(raw, MAX_JSON + 1)
    if len(decoded) > MAX_JSON or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
        raise ValueError('payload_size_or_gzip')
    def reject_constant(_):
        raise ValueError('nonfinite_json')
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('duplicate_json_key')
            out[k] = v
        return out
    payload = json.loads(decoded, parse_constant=reject_constant, object_pairs_hook=pairs)
    validate_payload(payload)
    return payload, 'sha256:' + hashlib.sha256(decoded).hexdigest()


def validate_payload(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('companies'), dict):
        raise ValueError('payload_schema')
    if not isinstance(payload.get('docs'), list) or len(payload['docs']) > 10000:
        raise ValueError('document_schema')
    if not isinstance(payload.get('fields'), dict) or len(payload['fields']) > 400 or len(payload['companies']) > 300:
        raise ValueError('fields_or_universe_schema')
    for symbol, company in payload['companies'].items():
        if (not re.fullmatch(r'[A-Z0-9]{1,10}', symbol) or not isinstance(company, dict)
                or company.get('ticker') != symbol or not isinstance(company.get('f'), dict)):
            raise ValueError('issuer_schema')
        issuer_scope = company.get('scope')
        if issuer_scope is not None and (not isinstance(issuer_scope, str)
                                        or issuer_scope not in ('social', 'consolidated')):
            raise ValueError('issuer_scope_schema')
    # Python's JSON decoder also accepts overflowing exponents unless checked.
    def check(value, depth=0):
        if depth > 30:
            raise ValueError('payload_depth')
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('nonfinite_json')
        if isinstance(value, dict):
            for item in value.values(): check(item, depth + 1)
        elif isinstance(value, list):
            for item in value: check(item, depth + 1)
    check(payload)


def _document(payload, fact):
    idx = fact.get('d')
    docs = payload['docs']
    label = docs[idx] if isinstance(idx, int) and not isinstance(idx, bool) and 0 <= idx < len(docs) else None
    page = fact.get('p')
    return dict(document=label[:400] if isinstance(label, str) else None,
                page=page if isinstance(page, int) and not isinstance(page, bool) and page > 0 else None,
                label=fact['l'][:300] if isinstance(fact.get('l'), str) else None,
                method=fact['m'][:100] if isinstance(fact.get('m'), str) else None, version='reported', provenance_grade='label_page_only',
                documents_certified=False)


def _row(payload, symbol, company, record, key, metric, unit, period, period_end, own, external):
    ext = external.get('reported') if isinstance(external, dict) else None
    ext = ext if isinstance(ext, dict) else {}
    own = own if isinstance(own, dict) else {}
    nv, sv = own.get('valeur'), ext.get('v')
    meta = payload['fields'].get(metric, {})
    provenance = _document(payload, ext)
    source_scope = company.get('scope')
    own_base = own.get('base')
    own_scope = scope(own_base)
    regimes = company.get('regimes') or {}
    source_regime = regimes.get(period_end[:4]) or company.get('regime')
    source_regime = source_regime[:100] if isinstance(source_regime, str) else None
    row = dict(symbol=symbol, screener_symbol=company['ticker'], metric=metric, nour_field=key, period=period,
               period_end=period_end, unit=unit, nour_value=nv if finite(nv) else None,
               screener_value=sv if finite(sv) else None, difference=None,
               scope=source_scope, screener_regime=source_regime,
               nour_provenance={k: own.get(k) for k in ('url', 'page', 'document_hash', 'validation_status', 'base', 'period_end')},
               screener_provenance=provenance, status='not_comparable', reason='dimensions_incomplete')
    own_currency = own.get('devise', record.get('devise'))
    row['nour_provenance'].update(currency=own_currency, unit=own.get('unite'))
    if unit == 'MMAD' and (own_currency != 'MAD' or company.get('currency') != 'MAD'):
        row['unit'] = ('Unités à rapprocher (Nour ' + str(own_currency or 'devise non précisée')
                       + ' / source ' + str(company.get('currency') or 'devise non précisée') + ')')
    if not row['nour_provenance']['url']:
        row['nour_provenance']['url'] = record.get('url')
    def stop(status, reason):
        row.update(status=status, reason=reason)
        return row
    if not finite(nv) or not finite(sv):
        return stop('missing', 'nour_missing_or_invalid' if not finite(nv) else 'screener_reported_missing_or_invalid')
    if company.get('unverified'):
        return stop('not_comparable', 'upstream_unverified')
    if (company.get('currency') != 'MAD' or own.get('devise', record.get('devise', 'MAD')) != 'MAD'):
        return stop('not_comparable', 'currency_mismatch')
    if not own.get('period_end'):
        return stop('not_comparable', 'nour_period_not_documented')
    if own['period_end'] != period_end:
        return stop('not_comparable', 'period_mismatch')
    if key == 'resultat_net_social' and source_scope != 'social':
        return stop('not_comparable', 'social_profit_is_not_group_profit')
    if unit != 'actions' and (source_scope not in ('consolidated', 'social') or own_scope != source_scope):
        return stop('not_comparable', 'accounting_scope_missing_or_mismatch')
    a, b = standard(own_base), standard(source_regime)
    if unit != 'actions' and (not a or not b or a != b):
        return stop('not_comparable', 'accounting_regime_missing_or_mismatch')
    expected_source_unit = {'MMAD': 'Mcur', 'MAD': 'cur_per_share', 'actions': 'count'}[unit]
    if own.get('unite') not in ({'MAD', 'DH'} if unit == 'MAD' else {unit}) or meta.get('unit') != expected_source_unit:
        return stop('not_comparable', 'unit_missing_or_mismatch')
    if unit == 'actions' and (nv <= 0 or sv <= 0 or int(nv) != nv or int(sv) != sv):
        return stop('not_comparable', 'invalid_share_count')
    if metric in ('dette_nette', 'tresorerie', 'dpa_propose'):
        return stop('not_comparable', 'definition_review_required')
    if ext.get('m') == 'derived':
        return stop('not_comparable', 'derived_definition_review_required')
    if ext.get('m') not in ('text_parse', 'visual', 'manual', 'ocr'):
        return stop('not_comparable', 'extraction_method_unrecognized')
    if not provenance['document'] or not provenance['page']:
        return stop('not_comparable', 'source_reference_incomplete')
    # Numeric agreement remains a comparison, never a primary-source validation.
    delta = sv - nv
    row['difference'] = round(delta, 9)
    if abs(delta) <= 1e-9:
        return stop('agreement', 'same_period_scope_currency_numeric_match')
    # A small absolute gap is a review category, never proof of rounding: the
    # screener does not publish a machine-readable precision contract.
    if unit != 'actions' and abs(delta) <= (0.0005 if unit == 'MMAD' else 0.005):
        return stop('rounding', 'small_difference_rounding_unverified')
    return stop('difference', 'primary_document_review_required')


def reconcile(payload, nour, *, checked_at=None, source_sha256=None, payload_sha256=None, symbols=None, source_codes=None):
    validate_payload(payload)
    stamp = clock(checked_at)
    generated = payload.get('generated_at')
    if not isinstance(generated, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?', generated):
        raise ValueError('source_generation_time_invalid')
    # A source without timezone stays explicitly unqualified; date only is used
    # for future detection, never an invented UTC conversion.
    today = datetime.fromisoformat(stamp).date()
    source_dt = datetime.fromisoformat(generated.replace('Z', '+00:00'))
    if (source_dt.utcoffset() is not None and source_dt > datetime.fromisoformat(stamp)) or date.fromisoformat(generated[:10]) > today:
        raise ValueError('source_generation_date_future')
    records = nour.get('records') if isinstance(nour, dict) else None
    if not isinstance(records, dict):
        raise ValueError('nour_schema')
    universe = sorted(set(symbols)) if symbols is not None else sorted(records)
    if any(not isinstance(s, str) or not re.fullmatch(r'[A-Z0-9]{1,10}', s) for s in universe):
        raise ValueError('universe_schema')
    codes = source_codes if isinstance(source_codes, dict) else {}
    mapped = [codes[s] for s in universe if s in codes]
    if (any(not isinstance(c, str) or not re.fullmatch(r'[A-Z0-9]{1,10}', c) for c in mapped)
            or len(set(mapped)) != len(mapped)):
        raise ValueError('identity_registry_ambiguous')
    rows, coverage = [], []
    for symbol in universe:
        record = records.get(symbol) or {}
        source_symbol = codes.get(symbol)
        company = payload['companies'].get(source_symbol)
        if not isinstance(company, dict):
            coverage.append(dict(symbol=symbol, screener_symbol=source_symbol, status='source_missing' if source_symbol else 'identity_unmapped', nour_available=symbol in records, periods=[]))
            continue
        if not REVIEWED_SOURCE_NAMES.get(source_symbol) or _plain(company.get('name')) != _plain(REVIEWED_SOURCE_NAMES[source_symbol]):
            coverage.append(dict(symbol=symbol, screener_symbol=source_symbol, status='identity_review_required', nour_available=symbol in records, periods=[]))
            continue
        periods = company['f']
        coverage.append(dict(symbol=symbol, screener_symbol=source_symbol, identity_method='explicit_source_code_registry_and_reviewed_name', status='available' if symbol in records else 'nour_missing', nour_available=symbol in records, periods=sorted(p for p in periods if re.fullmatch(r'FY\d{4}|H1-\d{4}', p))))
        year = record.get('exercice')
        if not isinstance(year, int) or isinstance(year, bool) or not 1900 < year < 2200:
            continue
        end = record.get('exercice_clos') or f'{year}-12-31'
        if end != f'{year}-12-31' or end > today.isoformat():
            continue
        own = record.get('faits') or {}
        for key, (metric, unit) in FIELDS.items():
            external = (periods.get(f'FY{year}') or {}).get(metric)
            if key not in own and not external:
                continue
            # Social/group fields with a distinct key are not fallback aliases.
            if key == 'resultat_net_social' and key not in own: continue
            if key == 'capitaux_propres_sociaux' and key not in own: continue
            rows.append(_row(payload, symbol, company, record, key, metric, unit, f'FY{year}', end, own.get(key), external))
        latest = record.get('latest_report') or {}
        send = latest.get('period_end')
        if isinstance(send, str) and re.fullmatch(r'\d{4}-06-30', send) and send <= today.isoformat():
            period = 'H1-' + send[:4]
            # The stored activity label, never the sector, distinguishes PNB.
            activity = {'PNB': ('PNB', 'produit_net_bancaire'),
                        'CA': ('CA', 'chiffre_affaires')}.get(record.get('semester_activity_label'),
                                                           ('activity_unspecified', 'revenue_millions'))
            for field, metric, key in [('reported_net_millions', 'RNPG', 'resultat_net_part_groupe'), ('revenue_millions', *activity)]:
                value = latest.get(field)
                external = (periods.get(period) or {}).get(metric) if metric != 'activity_unspecified' else None
                if value is None and not external: continue
                item = dict(valeur=value, unite='MMAD', devise=latest.get('currency'), period_end=send,
                            base=latest.get('accounting_basis'), url=latest.get('document_url'),
                            validation_status=latest.get('validation_status'))
                # A bare 'net' amount cannot establish group vs total profit.
                if metric == 'RNPG' and 'part du groupe' not in _plain(item['base']):
                    item['base'] = None
                unit = ('MMAD' if latest.get('currency') == 'MAD' else
                        'millions de ' + latest['currency'] if isinstance(latest.get('currency'), str) else
                        'millions — devise à confirmer')
                comparison = _row(payload, symbol, company, record, key, metric, unit, period, send, item, external)
                if metric == 'activity_unspecified':
                    comparison.update(status='not_comparable', reason='activity_label_unverified',
                                      activity_label=record.get('semester_activity_label'), screener_value=None, difference=None)
                rows.append(comparison)
    counts = Counter(r['status'] for r in rows)
    return dict(schema_version=1, version=VERSION, status='collected', checked_at=stamp,
                last_success_at=stamp, source_url=SOURCE_URL, source_generated_at=generated,
                source_timezone_attested=bool(re.search(r'Z$|[+-]\d{2}:\d{2}$', generated)),
                source_sha256=source_sha256, source_payload_sha256=payload_sha256,
                automatic_corrections=False, documents_certified=False,
                identity_provenance={'registry': 'data/source_codes.json', 'method': 'explicit_code_mapping_and_reviewed_source_name', 'isin_verified': False, 'registry_sha256': 'sha256:' + hashlib.sha256(json.dumps(codes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()},
                nour_facts_sha256='sha256:' + hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
                summary={**{s: counts[s] for s in STATUSES}, 'issuers': len(universe), 'nour_issuers': len(records),
                         'compared_issuers': len({r['symbol'] for r in rows}), 'source_issuers': len(payload['companies']), 'rows': len(rows)},
                rows=rows, coverage=coverage,
                notices=['Comparaison secondaire uniquement : aucune correction des faits, ratios ou scores.',
                         'Les documents et pages du screener sont des références déclarées sans URL ni empreinte primaire.',
                         'Les dérivés, définitions de dette/trésorerie/dividende et périmètres non comparables exigent une revue documentaire.',
                         'Aucun consensus, projection, second semestre calculé ou ratio au cours mobile n’est assimilé à un chiffre publié.',
                         'Un faible écart peut évoquer un arrondi mais ne le démontre pas. Une famille de référentiels identique ne certifie pas les choix de méthode ou leur transition.'])


def collect(nour, previous=None, *, now=None, fetcher=fetch, script=None, symbols=None, source_codes=None):
    stamp = clock(now)
    try:
        if script is None:
            script, final, _ = fetcher(SOURCE_URL, ORIGINS, timeout=20, max_bytes=MAX_SCRIPT)
            if final != SOURCE_URL:
                raise ValueError('unexpected_source_location')
        payload, payload_hash = decode_script(script)
        return reconcile(payload, nour, checked_at=stamp, source_sha256='sha256:' + hashlib.sha256(script).hexdigest(), payload_sha256=payload_hash, symbols=symbols, source_codes=source_codes)
    except Exception:
        # Do not publish raw errors, source content or arbitrary URLs. The last
        # success remains dated; a failed collection never resolves discrepancies.
        prior = deepcopy(previous) if isinstance(previous, dict) and previous.get('schema_version') == 1 and isinstance(previous.get('rows'), list) else {}
        prior.update(schema_version=1, version=VERSION, status='degraded' if prior.get('last_success_at') else 'unavailable',
                     checked_at=stamp, source_url=SOURCE_URL, automatic_corrections=False,
                     documents_certified=False, collection_error_code='source_unavailable_or_schema_rejected')
        prior.setdefault('rows', [])
        prior.setdefault('coverage', [])
        prior.setdefault('summary', {**{s: 0 for s in STATUSES}, 'issuers': 0, 'source_issuers': 0, 'rows': 0})
        return prior
