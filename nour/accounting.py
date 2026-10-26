"""Dated accounting evidence; never convert accounts or recompute market ratios."""
from copy import deepcopy
from datetime import date
from functools import lru_cache
import html
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from .sector_methods import guidance

PATH = Path(__file__).resolve().parents[1] / 'knowledge/accounting_methods.json'
VERSION = 'nour-accounting-v1'
LABELS = {'ifrs': 'IFRS', 'moroccan': 'Normes marocaines',
          'moroccan_credit': 'Référentiel marocain des établissements de crédit',
          'tunisian': 'Référentiel tunisien SCE', 'unknown': 'Référentiel à préciser'}


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower())
                   if unicodedata.category(c) != 'Mn')


def validate_catalog(data):
    if data.get('version') != VERSION:
        raise ValueError('Version du registre comptable inconnue')
    for source in data['sources'].values():
        url = urlsplit(source['url'])
        if (url.scheme != 'https' or url.username or url.password
                or url.hostname not in {'www.ammc.ma', 'www.ifrs.org', 'www.finances.gov.ma'}):
            raise ValueError('Source comptable primaire non autorisée')
        date.fromisoformat(source['reviewed_at'])
        if source.get('sha256') and not re.fullmatch(r'[a-f0-9]{64}', source['sha256']):
            raise ValueError('Empreinte comptable invalide')
    for topic in data['topics'].values():
        re.compile(topic['pattern'])
        if not topic['text'] or not topic['sources']:
            raise ValueError('Règle comptable sans explication ou preuve')
        for ref in topic['sources']:
            if ref['id'] not in data['sources']:
                raise ValueError('Source de règle inconnue')
            if 'page' in ref and (isinstance(ref['page'], bool) or not isinstance(ref['page'], int) or
                    ref['page'] not in data['sources'][ref['id']].get('checked_pages', [])):
                raise ValueError('Page de règle non contrôlée')
    for symbol, review in data['issuers'].items():
        if not re.fullmatch(r'[A-Z0-9]{2,5}', symbol) or review['framework'] not in LABELS:
            raise ValueError('Identité comptable invalide')
        date.fromisoformat(review['period_end'])
        source = data['sources'][review['source']]
        if not source.get('sha256') or source.get('review_kind') != 'selected_pages_visually_checked':
            raise ValueError('Revue de société sans PDF primaire contrôlé')
        pages = [review['basis_page'], *[p['page'] for p in review['policies']]]
        if review.get('comparability'):
            pages.append(review['comparability']['page'])
        for page in pages:
            if isinstance(page, bool) or not isinstance(page, int) or page not in source['checked_pages']:
                raise ValueError('Page comptable non contrôlée')
    return data


@lru_cache(maxsize=1)
def catalog():
    return validate_catalog(json.loads(PATH.read_text(encoding='utf-8')))


def declaration(label):
    """Classify only explicit source wording; the sector cannot supply a norm."""
    text = normalize(label or '')
    scope = ('social' if text.startswith('social') else
             'consolidated' if text.startswith('consolid') else 'unknown')
    framework = ('tunisian' if 'tunis' in text or 'sce)' in text else
                 'ifrs' if 'ifrs' in text else
                 'moroccan_credit' if 'etablissements de credit' in text or 'pcec' in text else
                 'moroccan' if 'maroc' in text or 'cgnc' in text else 'unknown')
    return scope, framework


def topic_ids(family):
    family = normalize(family)
    if family == 'banque':
        return ['general', 'credit', 'ifrs9']
    if family == 'assurance':
        return ['general', 'insurance']
    if 'courtage' in family or 'paiement' in family:
        return ['general', 'revenue', 'principal_agent']
    if 'credit' in family:
        return ['general', 'credit', 'leases']
    if 'promotion' in family:
        return ['general', 'revenue', 'pcsi', 'inventories']
    if 'foncieres' in family:
        return ['general', 'property', 'revenue']
    if 'informatique' in family or 'technolog' in family or 'telecomm' in family or 'pharmaceutique' in family:
        return ['general', 'revenue', 'research']
    if 'btp' in family:
        return ['general', 'revenue', 'provisions']
    if 'holding' in family:
        return ['general', 'social', 'dividends']
    return ['general', 'revenue', 'inventories', 'provisions']


def reference(ref, data=None):
    source = (data or catalog())['sources'][ref['id']]
    return {**deepcopy(source), 'page': ref.get('page'),
            'url': source['url'] + (f'#page={ref["page"]}' if ref.get('page') else '')}


def profile(symbol, fundamental, sector, asof):
    f = fundamental or {}
    scope, framework = declaration(f.get('accounting_basis'))
    family = guidance(symbol, {'sector': sector})['family']
    out = dict(version=VERSION, symbol=symbol, family=family,
        scope=scope, framework=framework, framework_label=LABELS[framework],
        declared_basis=f.get('accounting_basis'), period_end=f.get('period_end'),
        document_url=f.get('document_url'), exercise=f.get('exercise'),
        status='declared_to_review' if f.get('document_url') else 'missing',
        topics=topic_ids(family), policies=[], evidence=[], comparability=None,
        used_for_score=False, documents_certified=False,
        notice='Référentiel du document retenu ; aucune norme déduite du seul secteur.')
    recent = f.get('latest_report') or {}
    out['latest_publication'] = {k: deepcopy(recent.get(k)) for k in
        ('period_end', 'accounting_basis', 'document_url')}
    review = catalog()['issuers'].get(symbol)
    if not review or review['period_end'] != f.get('period_end'):
        return out
    source = catalog()['sources'][review['source']]
    if source['reviewed_at'] > asof or source['url'] != f.get('document_url'):
        return out
    known_hash = (f.get('provenance') or {}).get('document_hash')
    if known_hash and known_hash.removeprefix('sha256:') != source['sha256']:
        out['notice'] = 'Empreinte du document différente de la revue comptable : nouvelle lecture requise.'
        return out
    if scope != review['scope'] or framework != review['framework']:
        out['status'] = 'document_conflict'
        out['notice'] = 'Le libellé retenu et la revue primaire diffèrent ; rapprocher les périmètres avant comparaison.'
        return out
    out.update(status='primary_scoped_review', reviewed_at=source['reviewed_at'],
               basis_detail=review['basis_detail'], comparability=deepcopy(review.get('comparability')))
    out['evidence'] = [reference({'id': review['source'], 'page': review['basis_page']})]
    out['policies'] = [{**deepcopy(p), 'source': reference({'id': review['source'], 'page': p['page']})}
                       for p in review['policies']]
    out['notice'] = 'Pages sélectionnées du référentiel et des méthodes contrôlées ; aucune certification de tous les chiffres.'
    return out


def knowledge():
    data = catalog()
    return {'version': VERSION, 'question_pattern':data['question_pattern'], 'topics': {key: {**deepcopy(t),
            'sources': [reference(ref, data) for ref in t['sources']]}
            for key, t in data['topics'].items()}}


def definitions():
    return {'accounting_' + key: value['text'] + ' Sources : ' + '; '.join(
            ref['title'] + ' — ' + ref['url'] for ref in value['sources'])
            for key, value in knowledge()['topics'].items()}


def coverage(results):
    rows = [r.get('accounting_profile') or {} for r in results]
    return {'version': VERSION, 'universe': len(rows),
            'primary_scoped_reviews': sum(r.get('status') == 'primary_scoped_review' for r in rows),
            'declared_to_review': sum(r.get('status') == 'declared_to_review' for r in rows),
            'missing': sum(r.get('status') == 'missing' for r in rows),
            'conflicts': [r['symbol'] for r in rows if r.get('status') == 'document_conflict'],
            'documents_certified': False, 'used_for_score': False}


def details_html(p):
    if not p:
        return ''
    esc = lambda value: html.escape(str(value or 'Non précisé'), quote=True)
    items = ''.join(f'<li>{esc(v["text"])} <a href="{esc(v["source"]["url"])}" '
                    f'target="_blank" rel="noopener noreferrer">Page PDF {v["page"]}</a></li>'
                    for v in p.get('policies', []))
    return ('<details class="reading-details" data-accounting-methods><summary>Méthodes comptables et comparabilité</summary>'
            f'<p>{esc(p.get("framework_label"))} · {esc(p.get("declared_basis"))} · {esc(p.get("period_end"))}.</p>'
            f'<p>{esc(p.get("notice"))}</p><ul>{items}</ul>'
            '<a href="../comptabilite.html">Comprendre les référentiels par métier</a></details>')
