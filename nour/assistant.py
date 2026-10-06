"""Read-only, compact public facts for the separate explanatory assistant."""
from copy import deepcopy
import html
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 'nour-assistant-data-v1'
SYMBOL_FIELDS = ('symbol', 'name', 'asof', 'price', 'price_source', 'age_calendar_days',
                 'decision', 'technical', 'canonical_score', 'historical_statistics',
                 'market_risk', 'sector_comparison', 'quality')
FUNDAMENTAL_FIELDS = ('exercise', 'document_url', 'eps_mad', 'book_value_per_share_mad',
    'pe', 'pb', 'roe_pct', 'dividend_yield_pct', 'earnings_mmad', 'accounting_basis',
    'currency', 'net_debt_strict_mmad', 'net_debt_ebitda', 'pnb_mmad', 'pnb_growth_pct',
    'validation_status', 'warnings', 'latest_report', 'evidence', 'point_in_time_ready')


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def build_data(report):
    """Copy existing results; never call a scoring or forecasting function."""
    symbols = {}
    for item in report.get('results', []):
        row = {k: deepcopy(item.get(k)) for k in SYMBOL_FIELDS}
        f = item.get('fundamental') or {}
        row['fundamental'] = {k: deepcopy(f.get(k)) for k in FUNDAMENTAL_FIELDS}
        row['url'] = f"titres/{item['symbol']}.html"
        symbols[item['symbol']] = row
    return clean({'schema_version': VERSION, 'analysis_date': report['analysis_date'],
        'snapshot_updated': report.get('snapshot_updated'), 'score_version': report.get('score_version'),
        'market': deepcopy(report.get('market_overview') or {}),
        'masi_history': {d: v for d, v in report.get('masi_history', {}).items()
                         if d <= report['analysis_date']},
        'macro': deepcopy(report.get('macro') or {}), 'coverage': report.get('fundamental_coverage'),
        'health': {k: report.get(k) for k in ('health', 'overview_health', 'news_health')},
        'symbols': symbols,
        'definitions': {
            'score': 'Score descriptif de 0 à 100. Aucune performance prédictive validée. Actualités et IA ne contribuent pas au score.',
            'per': 'Cours / BPA annuel. Un semestre n’est jamais doublé. Ratio absent si bénéfice ou nombre d’actions non vérifié.',
            'pb': 'Cours / capitaux propres par action. Distinguer part du groupe et total consolidé.',
            'roe': 'Résultat annuel / capitaux propres de clôture, non capitaux propres moyens; lire le périmètre et les réserves.',
            'pnb': 'Produit net bancaire, distinct du chiffre d’affaires. Les ratios sectoriels ne sont pas interchangeables.',
            'probability': 'Une fréquence historique n’est pas une probabilité de prochaine séance. Les statistiques sont inconditionnelles et leurs limites restent visibles.',
            'assistant': 'Lecture des données publiées. L’IA optionnelle explique; elle ne calcule ni ne modifie les scores et ne passe aucun ordre.'}})


def context_for(data, symbols, question):
    """The server selects its own trusted snapshot, never facts sent by a client."""
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 2:
        raise ValueError('Choisissez un ou deux titres, ou MASI.')
    selected = {}
    for symbol in symbols:
        if symbol == 'MASI':
            selected['MASI'] = {'market': data['market'],
                'history_first': min(data['masi_history'], default=None),
                'history_last': max(data['masi_history'], default=None),
                'history_sessions': len(data['masi_history'])}
        elif symbol in data['symbols']:
            selected[symbol] = deepcopy(data['symbols'][symbol])
        else:
            raise ValueError('Titre absent du référentiel Nour.')
    import re
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', question)
    return {'analysis_date': data['analysis_date'], 'snapshot_updated': data.get('snapshot_updated'),
        'definitions': data['definitions'], 'selected': selected,
        'masi_dates': {d: data['masi_history'].get(d) for d in dates[:6]}}


def source_links(context):
    out = [{'label': 'Données et graphique MASI', 'url': 'index.html'}]
    for symbol, row in context['selected'].items():
        if symbol == 'MASI':
            continue
        out.append({'label': f'Fiche {symbol} · {row.get("asof")}', 'url': row['url']})
        f = row.get('fundamental') or {}
        for label, url in [('Comptes annuels', f.get('document_url')),
                           ('Dernière publication', (f.get('latest_report') or {}).get('document_url'))]:
            if isinstance(url, str) and urlsplit(url).scheme == 'https':
                out.append({'label': f'{symbol} · {label}', 'url': url})
    return out


def export(report, output):
    target = Path(output) / 'assistant-data.json'
    target.write_text(json.dumps(build_data(report), ensure_ascii=False, indent=2,
                                 allow_nan=False) + '\n', encoding='utf-8')


def panel(prefix=''):
    p = html.escape(prefix, quote=True)
    return (f'<button hidden type="button" id="assistant-open" class="assistant-launch" aria-haspopup="dialog" aria-controls="assistant-dialog">'
        '<span aria-hidden="true">✦</span> Assistant Nour</button>'
        f'<dialog id="assistant-dialog" class="assistant-dialog" data-prefix="{p}" aria-labelledby="assistant-title">'
        '<div class="assistant-head"><div><span class="eyebrow">Comprendre les données</span>'
        '<h2 id="assistant-title">Assistant Nour</h2><span id="assistant-mode" class="assistant-badge">Lecture des données · sans IA générative</span></div>'
        '<button type="button" id="assistant-close" aria-label="Fermer l’assistant">×</button></div>'
        '<p class="assistant-notice">Des réponses datées et leurs sources. Aucune prévision ni ordre de bourse.</p>'
        '<div class="assistant-tools"><label for="assistant-symbol">Contexte</label><select id="assistant-symbol"><option>MASI</option></select>'
        '<button type="button" id="assistant-clear">Effacer</button></div>'
        '<div id="assistant-messages" class="assistant-messages" role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions"></div>'
        '<div class="assistant-suggestions" aria-label="Questions proposées">'
        '<button type="button" data-assistant-question="Résume les données">Résumé</button>'
        '<button type="button" data-assistant-question="Quels fondamentaux sont disponibles ?">Fondamentaux</button>'
        '<button type="button" data-assistant-question="Explique les probabilités historiques">Statistiques</button>'
        '<button type="button" data-assistant-question="Explique le score">Score</button></div>'
        '<label id="assistant-ai-option" class="assistant-ai-option" hidden><input type="checkbox" id="assistant-ai">'
        '<span id="assistant-ai-label">Utiliser l’IA : envoyer la question et les données sélectionnées au fournisseur configuré.</span></label>'
        '<form id="assistant-form" class="assistant-form"><label for="assistant-question">Votre question</label>'
        '<div><textarea id="assistant-question" rows="2" maxlength="1200" placeholder="Ex. : explique le PER de JET" required></textarea>'
        '<button type="submit" id="assistant-send">Envoyer</button></div><p id="assistant-status" role="status">Les échanges restent dans cette fenêtre jusqu’à son rechargement.</p></form>'
        '</dialog><noscript><p class="fineprint">L’assistant nécessite JavaScript. Les données et sources restent consultables dans les fiches.</p></noscript>')
