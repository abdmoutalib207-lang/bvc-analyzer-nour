"""Issuer navigation and dated financial visuals, rendered from Nour facts only."""
from .bi_view import esc, finite, number
from .company_identity import company_logo
from .collection_view import collection_stamp
from .quote_view import quote_view, quote_clocks, date_label


def issuer_snapshot(item):
    """A short first reading of existing outputs; never calculate a new ratio."""
    f = item.get('fundamental') or {}
    cards = []
    for key, label, unit in (('pe', 'PER annuel', '×'), ('pb', 'Cours / fonds propres', '×'),
                             ('roe_pct', 'ROE annuel', '%'), ('earnings_mmad', 'Résultat attribuable', 'MMAD')):
        value = f.get(key)
        missing = 'Non disponible'
        if key == 'pe' and finite(f.get('earnings_mmad')) and f['earnings_mmad'] <= 0:
            missing = 'Non significatif'
        cards.append(f'<a class="issuer-keyfigure" href="#fondamentaux"><span>{label}</span>'
                     f'<strong>{number(value) if finite(value) else "—"}</strong>'
                     f'<small>{unit if finite(value) else missing}</small></a>')
    warnings = f.get('warnings') or []
    alerts = []
    if (f.get('debt_reconciliation') or {}).get('status') == 'unresolved':
        alerts.append('Dette publiée et calcul Nour à rapprocher')
    if (f.get('financial_audit') or {}).get('blocked_metrics'):
        alerts.append('Certains ratios restent non disponibles')
    if any(any(word in str(w).lower() for word in ('pcsi', 'reconnaissance', 'méthode constante')) for w in warnings):
        alerts.append('Comparabilité comptable à vérifier')
    if warnings:
        alerts.append(f'{len(warnings)} réserve(s) financière(s)')
    if item.get('decision') in ('SUSPENDU', 'INDISPONIBLE', 'LIMITÉ'):
        alerts.insert(0, 'Données ' + item['decision'].lower())
    market_issue = bool(item.get('resilience', {}).get('anomalies') or (item.get('quality') or {}).get('issues'))
    if market_issue:
        alerts.append('Historique : points de vigilance')
    links = (' <a href="#verifications">Réserves financières</a>' if warnings or (f.get('financial_audit') or {}).get('blocked_metrics') or (f.get('debt_reconciliation') or {}).get('status') == 'unresolved' else '')
    if market_issue or item.get('decision') in ('SUSPENDU', 'INDISPONIBLE', 'LIMITÉ'):
        links += ' <a href="#qualite-donnees">État des données</a>'
    notice = ('<div class="issuer-attention" data-issuer-attention><span>À noter</span> '
              + ' · '.join(esc(x) for x in alerts)
              + links + '</div>') if alerts else ''
    return ('<div class="issuer-keyfigures" data-issuer-snapshot>' + ''.join(cards) + '</div>'
            f'<p class="issuer-period">Comptes annuels {esc(f.get("exercise") or "non documentés")} · '
            f'cours de référence du {date_label(item.get("asof"))}</p>' + notice)


def issuer_heading(item, record, collection=None):
    history = item.get('history_readiness') or {}
    change = ''
    view = quote_view(item, record)
    if view['change_pct'] is not None:
        delta = view['change_pct']
        change = (f'<span class="quote-change {"gain" if delta >= 0 else "loss"}">'
                  f'{"+" if delta >= 0 else ""}{number(delta)} %</span>'
                  f'<small>Depuis la clôture disponible du {date_label(view["reference_session"])}</small>')
    links = ''.join(f'<a href="#{key}">{label}</a>' for key, label in (
        ('graphique', 'Graphique'), ('metier', 'Métier'), ('technique', 'Technique'),
        ('fondamentaux', 'Comptes & ratios'), ('risques', 'Risques'),
        ('historique', 'Historique & sources')))
    return ('<div class="hero issuer-hero"><div><a href="../index.html" class="muted">← Les 80 valeurs</a>'
            f'<div class="eyebrow">{esc(record.get("sector") or "Action cotée")} · {esc(item["symbol"])}</div>'
            f'<div class="company-heading">{company_logo(item["symbol"], "../")}<h1>{esc(record["name"])}</h1></div>'
            f'<span class="status {esc(item["decision"])}">{esc(item["decision"])}</span>'
            f'<button type="button" class="issuer-ask" data-assistant-question="Fais une synthèse complète de {esc(item["symbol"])} : marché, technique, fondamentaux, risques, qualité et sources. Distingue annuel et semestre et conserve les réserves.">Lire le dossier avec Nour</button></div>'
            f'<div class="issuer-quote" data-quote-mode="{"provisional" if view["provisional"] else "close"}"><span>{view["label"]}</span>'
            f'<strong data-primary-price>{number(view["price"])} <small>MAD</small></strong>{change}'
            + quote_clocks(view, compact=True)
            + (f'<p class="quote-reference">Clôture de référence : {number(item.get("price"))} MAD · {date_label(item.get("asof"))}. Les indicateurs et ratios restent liés à cette clôture.</p>' if view['provisional'] else '')
            + '<p><a href="../sources.html#marche">Sources du cours</a></p><details class="quote-clock-details"><summary>Vérification de la collecte</summary><div class="quote-collector-check">'
            + collection_stamp((collection or {}).get('checked_at'), 'Dernière tentative de collecte' if (collection or {}).get('result')=='error' else 'Dernière vérification des sources') + '</div>'
            + '</div></div>'
            f'<nav class="issuer-nav" aria-label="Rubriques de la valeur">{links}</nav>')


def documentary_status(item):
    status = item.get('issuer_status') or {}
    provenance = item.get('history_provenance') or {}
    parts = []
    if status:
        links = ' · '.join(f'<a href="{esc(s["url"])}" rel="noopener noreferrer">{esc(s["label"])}</a>' for s in status.get('sources', []))
        parts.append(f'<h2>{esc(status["label"])}</h2><p>{esc(status["reason"])}</p>'
                     f'<p>Dernier dépôt identifié : {esc(status.get("last_known_filing_date"))} ; période : {esc(status.get("last_known_financial_period"))}. Observation au {esc(status.get("observed_asof"))}.</p>'
                     f'<p>{links}</p><p class="fineprint">{esc(status.get("validation"))}</p>')
    if provenance:
        parts.append(f'<h2>Historique rapproché</h2><p>{esc(provenance.get("notice"))}</p>'
                     f'<p>Période opérateur : {esc(" → ".join(provenance["operator_period"]))}. '
                     f'{provenance["added"]} séances ajoutées ; {provenance["replaced"]} observations corrigées.</p>'
                     f'<p><a href="{esc(provenance["source_url"])}">Série source figée</a> · '
                     f'<a href="{esc(provenance["manifest_url"])}">Manifeste et empreinte de l’export</a></p>')
    return '<section class="panel">'+''.join(parts)+'</section>' if parts else ''


def financial_history(item):
    """Plot only explicitly dated annual comparatives from the same source/scope.

    A different document, unit, missing date or basis refuses the comparison.
    No historical year or interim date is inferred from a field name.
    """
    f = item.get('fundamental') or {}
    evidence = f.get('evidence') or {}
    plots = []
    for key, label in (('chiffre_affaires', 'Chiffre d’affaires'),
                       ('produit_net_bancaire', 'Produit net bancaire'),
                       ('capitaux_propres_part_groupe', 'Capitaux propres part du groupe'),
                       ('capitaux_propres_sociaux', 'Capitaux propres sociaux')):
        current = evidence.get(key) or {}
        try:
            year = int(str(current.get('period_end', ''))[:4])
        except (ValueError, TypeError):
            continue
        previous = evidence.get(f'{key}_{year - 1}') or {}
        expected = [f'{year - 1}-12-31', f'{year}-12-31']
        if (f.get('currency') != 'MAD' or current.get('period_end') != f.get('period_end')
                or [previous.get('period_end'), current.get('period_end')] != expected
                or current.get('unit') != 'MMAD' or previous.get('unit') != 'MMAD'
                or not current.get('accounting_basis')
                or previous.get('accounting_basis') != current.get('accounting_basis')
                or not str(current.get('document_url', '')).startswith('https://')
                or previous.get('document_url') != current.get('document_url')
                or not all(finite(x.get('value')) and x.get('currency') == 'MAD'
                           and isinstance(x.get('page'), int) and not isinstance(x.get('page'), bool)
                           and x['page'] > 0 for x in (previous, current))):
            continue
        amounts = [previous['value'], current['value']]
        low, high = min(0, *amounts), max(0, *amounts)
        span = high - low or 1
        y = lambda value: 178 - 140 * (value - low) / span
        zero = y(0)
        shapes = []
        for idx, (entry, value) in enumerate(zip((previous, current), amounts)):
            x = 85 + idx * 160
            shapes.append(f'<rect x="{x}" y="{min(zero, y(value)):.2f}" width="64" '
                          f'height="{abs(zero - y(value)):.2f}" class="financial-bar financial-bar-{idx}"/>'
                          f'<text x="{x+32}" y="{max(17, min(zero, y(value))-9):.2f}" text-anchor="middle">{number(value)}</text>'
                          f'<text x="{x+32}" y="207" text-anchor="middle">{esc(entry["period_end"])}</text>')
        sources = ''.join(f'<a href="{esc(entry["document_url"])}#page={esc(entry.get("page"))}" '
                          f'target="_blank" rel="noopener noreferrer">{esc(entry["period_end"])} · p. {esc(entry.get("page"))}</a>'
                          for entry in (previous, current))
        plots.append(f'<figure class="financial-history"><figcaption>{label}<small>Comptes annuels · MMAD</small></figcaption>'
                     f'<svg viewBox="0 0 390 225" role="img" aria-label="{esc(label)} : {number(amounts[0])} MMAD au {expected[0]}, {number(amounts[1])} MMAD au {expected[1]}">'
                     f'<line x1="35" x2="365" y1="{zero:.2f}" y2="{zero:.2f}" class="chart-grid"/>{"".join(shapes)}</svg>'
                     f'<div class="financial-chart-sources">{sources}</div>'
                     f'<p class="fineprint">{esc(current["accounting_basis"])}. Comparatif du même document ; lire les réserves ci-dessous.</p></figure>')
    if not plots:
        return '<p class="fineprint">Évolution financière : aucun comparatif annuel explicitement daté et compatible n’est encore disponible pour un graphique.</p>'
    return '<div class="financial-history-grid">' + ''.join(plots) + '</div>'
