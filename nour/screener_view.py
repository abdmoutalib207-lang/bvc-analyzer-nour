"""A documentary comparison is visible evidence, never a calculation input."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from html import escape
import math
import re

from .official_sources import safe_url

SOURCE = 'https://ms-screener.vercel.app/app.js'
# Explicit origins already used by Nour's official registry or reviewed facts.
# A URL supplied by the external screener cannot extend this set.
ORIGINS = frozenset({
    'https://ammc.ma', 'https://www.ammc.ma', 'https://alliances.co.ma',
    'https://www.alliances.co.ma', 'https://ir.attijariwafabank.com',
    'https://marsamaroc.co.ma', 'https://www.marsamaroc.co.ma',
    'https://totalenergies.ma', 'https://www.totalenergies.ma',
    'https://vicenne.com', 'https://www.vicenne.com',
    'https://www.autohall.ma', 'https://www.taqamorocco.ma',
})
LABELS = {
    'agreement': 'Concordance numérique', 'rounding': 'Écart faible · arrondi à vérifier',
    'difference': 'Écart à rapprocher', 'not_comparable': 'Bases non comparables',
    'missing': 'Donnée manquante pour la comparaison',
}
STATES = {
    'collected': 'Comparaison disponible', 'degraded': 'Collecte dégradée',
    'unavailable': 'Source indisponible', 'not_available': 'Comparaison indisponible',
    'not_observed': 'Comparaison non encore exécutée',
    'not_yet_available': 'État postérieur à la date consultée',
    'stale': 'Comparaison ancienne', 'stale_inputs': 'Données Nour modifiées depuis la comparaison',
}
METRICS = {
    'CA': 'Chiffre d’affaires', 'PNB': 'Produit net bancaire', 'RNPG': 'Résultat net part du groupe',
    'resultat_net_total': 'Résultat net total', 'capitaux_propres_groupe': 'Capitaux propres du groupe',
    'capitaux_propres': 'Capitaux propres', 'REX': 'Résultat d’exploitation',
    'charges_fin_nettes': 'Résultat financier', 'EBE': 'Excédent brut d’exploitation',
    'dette_financiere': 'Dette financière', 'dette_nette': 'Dette nette', 'tresorerie': 'Trésorerie',
    'total_actif': 'Total actif', 'nb_titres': 'Nombre d’actions', 'dpa_propose': 'Dividende par action proposé',
    'activity_unspecified': 'Niveau d’activité semestriel · libellé à vérifier',
}
REASONS = {
    'dimensions_incomplete': 'Dimensions comptables incomplètes',
    'nour_missing_or_invalid': 'Valeur Nour absente ou invalide',
    'screener_reported_missing_or_invalid': 'Montant publié absent ou invalide dans la source externe',
    'upstream_unverified': 'Le screener signale lui-même ce dossier non vérifié',
    'currency_mismatch': 'Devises absentes ou différentes',
    'nour_period_not_documented': 'Période du montant Nour non documentée',
    'period_mismatch': 'Périodes différentes',
    'social_profit_is_not_group_profit': 'Le résultat social ne remplace pas le résultat du groupe',
    'accounting_scope_missing_or_mismatch': 'Périmètres comptables absents ou différents',
    'accounting_regime_missing_or_mismatch': 'Référentiels comptables absents ou différents',
    'unit_missing_or_mismatch': 'Unités absentes ou différentes',
    'invalid_share_count': 'Nombre d’actions invalide',
    'definition_review_required': 'Définition comptable à rapprocher dans les publications',
    'derived_definition_review_required': 'Calcul externe : formule et composants à vérifier',
    'extraction_method_unrecognized': 'Méthode d’extraction non reconnue',
    'source_reference_incomplete': 'Document ou page source manquant',
    'same_period_scope_currency_numeric_match': 'Même période, périmètre et devise ; montants concordants',
    'small_difference_rounding_unverified': 'Faible écart numérique ; l’arrondi reste à confirmer',
    'primary_document_review_required': 'Écart à vérifier dans les documents officiels',
    'activity_label_unverified': 'Nature de l’activité semestrielle à confirmer ; aucune assimilation au chiffre d’affaires',
}
SCOPES = {'social': 'Comptes sociaux', 'consolidated': 'Comptes consolidés'}
METHODS = {'text_parse': 'Extraction de texte', 'visual': 'Lecture visuelle déclarée',
           'manual': 'Saisie manuelle déclarée', 'ocr': 'Reconnaissance de caractères',
           'derived': 'Montant calculé'}
VERSIONS = {'reported': 'Publié', 'restated': 'Retraité', 'proforma': 'Pro forma'}


def _esc(value):
    text = str(value if value is not None else '—')
    return escape(text[:2000] + ('…' if len(text) > 2000 else ''), quote=True)


def _label(mapping, value, default='À préciser'):
    """Schema drift must not turn a diagnostic code into an unhashable key."""
    return mapping.get(value, value) if isinstance(value, str) else default


def _day(value):
    try:
        return date.fromisoformat(value[:10]) if isinstance(value, str) else None
    except ValueError:
        return None


def _totals(rows):
    counts = Counter(row.get('status') for row in rows
                     if isinstance(row, dict) and isinstance(row.get('status'), str))
    return {**{key: counts[key] for key in LABELS}, 'rows': len(rows),
            'issuers': len({str(row.get('symbol')) for row in rows if isinstance(row, dict)})}


def visible_state(state, asof, nour_facts_sha256=None):
    """Return a detached dated view; never turn stale/future data into proof."""
    out = deepcopy(state) if isinstance(state, dict) else {'status': 'not_observed'}
    out.setdefault('status', 'not_observed')
    rows = out.get('rows') if isinstance(out.get('rows'), list) else []
    out['rows'] = [r for r in rows if isinstance(r, dict)]
    out['notices'] = list(out.get('notices') or []) if isinstance(out.get('notices'), list) else []
    on = _day(asof)
    if on is not None:
        clocks = [out.get(key) for key in ('checked_at', 'last_success_at', 'source_generated_at')]
        if any(day is not None and day > on for day in map(_day, clocks)):
            out.update(status='not_yet_available', rows=[], coverage=[], summary=_totals([]))
            notice = 'État daté après la date consultée : les chiffres de comparaison ne sont pas affichés.'
            if notice not in out['notices']:
                out['notices'].append(notice)
            return out
        past_rows = [r for r in out['rows'] if _day(r.get('period_end')) is None or _day(r['period_end']) <= on]
        if len(past_rows) != len(out['rows']):
            out['rows'] = past_rows
            out['summary'] = _totals(past_rows)
            out['notices'].append('Les périodes financières postérieures à la date consultée sont exclues.')
        last = _day(out.get('last_success_at'))
        if last is not None and (on - last).days > 7:
            if out.get('status') != 'stale_inputs':
                out['status'] = 'stale'
            out['notices'].append(f'Dernier succès ancien : {(on - last).days} jours. Ces observations datées sont conservées pour examen.')
    expected = out.get('nour_facts_sha256')
    if (nour_facts_sha256 is not None and expected != nour_facts_sha256
            and (out['rows'] or out.get('last_success_at'))):
        out['status'] = 'stale_inputs'
        out['notices'].append('Les faits Nour ont changé ou leur empreinte manque : relancer la comparaison avant de conclure.')
    out.setdefault('summary', _totals(out['rows']))
    # Rendering an already dated state must not repeat diagnostic sentences.
    out['notices'] = list(dict.fromkeys(str(n) for n in out['notices']))
    return out


def _value(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return '—'
    try:
        return _esc(str(value).replace('.', ',')) if math.isfinite(value) else '—'
    except OverflowError:
        return '—'


def _link(url):
    if not isinstance(url, str) or not re.fullmatch(r'https://[a-zA-Z0-9.-]+/[^\s<>"\\]*', url):
        return None
    return safe_url(url, ORIGINS)


def _nour_provenance(row):
    p = row.get('nour_provenance') or {}
    p = p if isinstance(p, dict) else {}
    url = _link(p.get('url'))
    source = (f'<a href="{_esc(url)}" target="_blank" rel="noopener noreferrer">Document Nour ↗</a>'
              if url else 'Document Nour : lien absent ou non autorisé')
    return (source + f'<br>Page : {_esc(p.get("page"))}<br>Période : {_esc(p.get("period_end"))}'
            f'<br>Base : {_esc(p.get("base"))}<br>Revue : {_esc(p.get("validation_status"))}'
            f'<br><small class="sc-hash">Empreinte : {_esc(p.get("document_hash"))}</small>')


def _external_provenance(row):
    p = row.get('screener_provenance') or {}
    p = p if isinstance(p, dict) else {}
    return (f'Document indiqué : {_esc(p.get("document"))}<br>Page indiquée : {_esc(p.get("page"))}'
            f'<br>Libellé : {_esc(p.get("label"))}<br>Méthode : {_esc(_label(METHODS, p.get("method")))}'
            f'<br>Version : {_esc(_label(VERSIONS, p.get("version")))}<br>Référentiel : {_esc(row.get("screener_regime"))}'
            '<br><small>Référence externe ; cette mention ne prouve pas la lecture du PDF.</small>')


def _notices(state):
    items = state.get('notices') if isinstance(state.get('notices'), list) else []
    error = state.get('collection_error_code')
    if error:
        items = [*items, 'Dernier essai de collecte : ' + str(error)]
    return '<ul>' + ''.join('<li>' + _esc(x) + '</li>' for x in items) + '</ul>' if items else ''


def _dates(state):
    return (f'<p>Dernier essai : {_esc(state.get("checked_at"))} · '
            f'Dernier succès : {_esc(state.get("last_success_at"))} · '
            f'Génération indiquée par la source : {_esc(state.get("source_generated_at"))}.</p>')


def _coverage_counts(summary):
    labels = [('issuers', 'Univers suivi'), ('source_issuers', 'Sociétés présentes dans la source'),
              ('nour_issuers', 'Dossiers financiers Nour'), ('compared_issuers', 'Sociétés avec lignes de comparaison')]
    return '<p>' + ' · '.join(label + ' : <strong>' + _value(summary[key]) + '</strong>'
                             for key, label in labels if key in summary) + '.</p>'


def _gaps(state):
    labels = {'source_missing': 'Société absente de la source externe',
              'nour_missing': 'Dossier financier Nour absent',
              'identity_review_required': 'Identité de la société à rapprocher',
              'identity_unmapped': 'Correspondance d’identité non renseignée',
              'missing': 'Couverture à compléter'}
    coverage = state.get('coverage')
    gaps = [r for r in coverage if isinstance(r, dict) and r.get('status') != 'available'] if isinstance(coverage, list) else []
    if not gaps:
        return ''
    return ('<section class="panel"><h2>Lignes non comparées</h2>'
            '<p>Ces sociétés restent dans la couverture cible ; leur absence de tableau détaillé a les motifs suivants.</p><ul>'
            + ''.join('<li><strong>' + _esc(r.get('symbol')) + '</strong> : '
                      + _esc(_label(labels, r.get('status'), 'Couverture à préciser'))
                      + (' · dossier Nour présent' if r.get('nour_available') is True else ' · dossier Nour absent ou non confirmé')
                      + '</li>' for r in gaps) + '</ul></section>')


def summary_card(state, asof=None):
    state = visible_state(state, asof)
    summary = state.get('summary') or {}
    summary = summary if isinstance(summary, dict) else {}
    return ('<section class="panel" id="contre-verification"><h2>Contre-vérification des fondamentaux</h2>'
            f'<p>{_esc(_label(STATES, state.get("status"), STATES["not_observed"]))}. '
            f'{_value(summary.get("issuers", 0))} sociétés dans l’univers suivi ; '
            f'{_value(summary.get("difference", 0))} écarts numériques à rapprocher.</p>'
            + _dates(state) + _notices(state)
            + '<p>Comparer Nour et MS Screener ne certifie aucun document et ne modifie aucun chiffre ni score.</p>'
            '<a href="contre-verification.html">Voir les comparaisons, les bases et les sources ↗</a></section>')


def body(state, asof=None):
    state = visible_state(state, asof)
    summary = state.get('summary') or {}
    summary = summary if isinstance(summary, dict) else {}
    groups = defaultdict(list)
    for row in state.get('rows') or []:
        if isinstance(row, dict):
            groups[str(row.get('symbol') or 'Titre non identifié')].append(row)
    counters = ''.join(f'<li>{_esc(label)} : <strong>{_value(summary.get(key, 0))}</strong></li>'
                       for key, label in LABELS.items())
    panels = []
    for symbol, rows in sorted(groups.items()):
        cells = []
        for row in rows:
            status = _label(LABELS, row.get('status'))
            metric = ('Résultat net social' if row.get('nour_field') == 'resultat_net_social'
                      else _label(METRICS, row.get('metric')))
            cells.append('<tr><th scope="row">' + _esc(metric)
                + ('<br><small>Libellé conservé : ' + _esc(row.get('activity_label')) + '</small>'
                   if row.get('activity_label') else '')
                + f'<details><summary>Clé technique</summary><small>{_esc(row.get("nour_field"))}</small></details></th>'
                f'<td>{_esc(row.get("period"))}<br>{_esc(row.get("period_end"))}'
                f'<br>{_esc(_label(SCOPES, row.get("scope")))}<br>{_esc(row.get("unit"))}</td>'
                f'<td>{_value(row.get("nour_value"))}</td><td>{_value(row.get("screener_value"))}</td>'
                f'<td>{_value(row.get("difference"))}</td><td>{_esc(status)}<br>{_esc(_label(REASONS, row.get("reason")))}</td>'
                '<td>' + _nour_provenance(row) + '</td><td>' + _external_provenance(row) + '</td></tr>')
        panels.append('<details class="panel reading-details" data-comparison-symbol="' + _esc(symbol) + '"><summary>' + _esc(symbol)
            + f' · {len(rows)} comparaison(s)</summary><div class="tablewrap"><table class="sc-table">'
            '<thead><tr><th>Indicateur</th><th>Période, périmètre et unité</th><th>Nour</th>'
            '<th>MS Screener</th><th>Écart MS − Nour</th><th>Lecture</th><th>Preuve Nour</th>'
            '<th>Référence externe</th></tr></thead><tbody>' + ''.join(cells)
            + '</tbody></table></div></details>')
    return ('<style>.sc-table{min-width:1050px}.sc-table td,.sc-table th{vertical-align:top;white-space:normal}'
            '.sc-table td{min-width:100px}.sc-table td:nth-last-child(-n+2){min-width:220px}'
            '.sc-hash{overflow-wrap:anywhere}.sc-audit .tablewrap{overflow-x:auto;max-width:100%}'
            '.sc-audit summary{cursor:pointer}.sc-audit ul{padding-left:1.4rem}</style>'
            '<main class="sc-audit" data-screener-audit><a href="sources.html">← Sources</a><div class="hero"><div>'
            '<span class="eyebrow">Audit documentaire distinct du moteur</span>'
            '<h1>Contre-vérification financière</h1>'
            '<p>Comparer les observations de Nour et de MS Screener, puis remonter aux publications.</p>'
            '</div></div><section class="panel"><h2>'
            + _esc(_label(STATES, state.get('status'), STATES['not_observed']))
            + '</h2>' + _dates(state) + _notices(state)
            + '<p><strong>Aucune correction automatique. Aucun document certifié.</strong> '
            'Une concordance numérique ne constitue pas une vérification indépendante du PDF. '
            'Les écarts, les arrondis et les différences de période, périmètre ou méthode restent distincts.</p>'
            f'<p>Source secondaire : <a href="{SOURCE}" target="_blank" rel="noopener noreferrer">'
            'MS Screener, données publiquement embarquées</a>.<br>'
            f'<small class="sc-hash">Empreinte de collecte : {_esc(state.get("source_sha256"))}</small></p>'
            + _coverage_counts(summary)
            + '<p>La couverture cible comprend les 80 sociétés Nour ; un chiffre absent de la source externe reste manquant.</p>'
            '<ul>' + counters + '</ul><a href="screener-reconciliation.json">Télécharger le relevé daté JSON</a>'
            '</section>' + _gaps(state) + '<section><h2>Comparaisons par société</h2><p>Ouvrez une société pour consulter '
            'toutes ses lignes, y compris les concordances. Les valeurs sont exprimées dans l’unité de chaque ligne.</p>'
            + ''.join(panels) + ('' if panels else '<p>Aucune ligne comparable disponible pour cette date.</p>')
            + '</section></main>')
