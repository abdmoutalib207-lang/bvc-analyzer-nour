"""Issuer navigation and dated financial visuals, rendered from Nour facts only."""
from .bi_view import esc, finite, number
from .company_identity import company_logo
from .collection_view import collection_stamp


def issuer_heading(item, record, collection=None):
    history = item.get('history_readiness') or {}
    bars = record.get('candles') or []
    change = ''
    if (len(bars) > 1 and bars[-1].get('d') == item.get('asof')
            and finite(bars[-2].get('c')) and bars[-2]['c'] > 0
            and finite(item.get('price'))):
        delta = 100 * (item['price'] / bars[-2]['c'] - 1)
        change = (f'<span class="quote-change {"gain" if delta >= 0 else "loss"}">'
                  f'{"+" if delta >= 0 else ""}{number(delta)} %</span>'
                  f'<small>Depuis la clôture disponible du {esc(bars[-2]["d"])}</small>')
    links = ''.join(f'<a href="#{key}">{label}</a>' for key, label in (
        ('graphique', 'Graphique'), ('technique', 'Technique'),
        ('fondamentaux', 'Comptes & ratios'), ('risques', 'Risques'),
        ('historique', 'Historique & sources')))
    return ('<div class="hero issuer-hero"><div><a href="../index.html" class="muted">← Les 80 valeurs</a>'
            f'<div class="eyebrow">{esc(record.get("sector") or "Action cotée")} · {esc(item["symbol"])}</div>'
            f'<div class="company-heading">{company_logo(item["symbol"], "../")}<h1>{esc(record["name"])}</h1></div><p>{esc(history.get("label"))}</p>'
            f'<span class="status {esc(item["decision"])}">{esc(item["decision"])}</span>'
            f'<button type="button" class="issuer-ask" data-assistant-question="Fais une synthèse complète de {esc(item["symbol"])} : marché, technique, fondamentaux, risques, qualité et sources. Distingue annuel et semestre et conserve les réserves.">Lire le dossier avec Nour</button></div>'
            '<div class="issuer-quote"><span>Dernière clôture attestée</span>'
            f'<strong>{number(item.get("price"))} <small>MAD</small></strong>{change}'
            f'<p>Séance {esc(item.get("asof"))}<br><a href="../sources.html#marche">Sources du cours</a></p>'
            + collection_stamp((collection or {}).get('checked_at'), 'Dernière tentative de collecte' if (collection or {}).get('result')=='error' else 'Dernier passage du collecteur')
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
