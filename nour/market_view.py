"""Market-first HTML. Index history contains closes, not fabricated OHLCV."""
import html
import json
from .chart_view import navigation, explorer_footer
from .report_contracts import volume_reconciliation
from .collection_view import collection_stamp


def fmt(v, digits=2):
    return '—' if v is None else f'{float(v):,.{digits}f}'.replace(',', ' ').replace('.', ',')


def esc(v):
    return html.escape(str(v if v is not None else '—'), quote=True)


def masi_svg(points):
    if not points:
        return '<div class="fallback">Historique MASI indisponible.</div>'
    values = [v for _,v in points]
    lo, hi = min(values), max(values)
    padding = max((hi-lo)*.12, 1)
    lo, hi = lo-padding, hi+padding
    xy = ' '.join(f'{65+810*i/max(1,len(points)-1):.2f},{260-230*(v-lo)/(hi-lo):.2f}'
                  for i,(_,v) in enumerate(points))
    grid = ''.join(f'<line x1="65" x2="875" y1="{30+i*57.5}" y2="{30+i*57.5}" stroke="#29454c"/>'
                   f'<text x="2" y="{34+i*57.5}">{fmt(hi-(hi-lo)*i/4,0)}</text>' for i in range(5))
    return (f'<svg viewBox="0 0 900 300" tabindex="0" role="img" aria-label="Historique des clôtures MASI ; utilisez les flèches pour parcourir les séances">{grid}'
            f'<polygon points="65,260 {xy} 875,260" fill="#b4e283" opacity=".07"/>'
            f'<polyline points="{xy}" fill="none" stroke="#b4e283" stroke-width="2.5"/>'
            f'<text x="65" y="288">{esc(points[0][0])}</text><text x="783" y="288">{esc(points[-1][0])}</text></svg>')


def market_panel(report):
    overview = report.get('market_overview') or {}
    index = overview.get('masi') or {}
    points = sorted((report.get('masi_history') or {}).items())
    points = [(d,v) for d,v in points if d <= overview.get('asof', report['analysis_date'])]
    last = points
    coverage = (f'Historique disponible : {esc(points[0][0])} → {esc(points[-1][0])}'
                f' · {len(points)} séances' if points else 'Historique MASI indisponible')
    change = index.get('change_pct')
    tone = 'gain' if change is not None and change > 0 else 'loss' if change is not None and change < 0 else 'muted'
    provisional = overview.get('status') == 'intraday'
    label = 'Point de séance provisoire' if provisional else 'Dernière clôture disponible'
    summary = (f'<section class="panel market-panel"><div class="focus-header"><div><span class="eyebrow">MASI · Casablanca</span>'
               f'<h2>{label} · {esc(overview.get("asof"))}</h2>{collection_stamp(overview.get("observed_at"), "Relevé marché collecté")}<div class="index-value">{fmt(index.get("value"))}<small>points</small></div></div>'
               f'<div class="index-change {tone}">{fmt(change)} %<small>{fmt(index.get("variation_points"))} points</small></div></div>'
               '<div class="market-stats">'
               f'<div><span>Clôture précédente</span><strong>{fmt(index.get("veille"))}</strong></div>'
               f'<div><span>Depuis le début de l’année</span><strong>{fmt(index.get("ytd_pct"))} %</strong></div>'
               f'<div><span>Plus haut de séance</span><strong>{fmt(overview.get("high"))}</strong></div>'
               f'<div><span>Plus bas de séance</span><strong>{fmt(overview.get("low"))}</strong></div></div>'
               '<div class="chart-root" data-masi-chart>'
               f'<p class="panel-sub" data-masi-coverage>{coverage}</p>'
               '<div class="chart-toolbar"><div class="periods" aria-label="Période MASI">'
               + ''.join(f'<button type="button" data-masi-period="{n}" title="{str(n) + " séances disponibles" if n else "Tout l’historique disponible"}" aria-pressed="{str(n==0).lower()}">{title}</button>'
                         for n,title in ((21,'1M'),(63,'3M'),(252,'1A'),(756,'3A'),(0,'Tout')))
               + '</div></div><div class="chart-toolbar">' + navigation() + '</div>'
               f'<div class="chart masi-chart" tabindex="0" aria-label="Graphique MASI, navigation au clavier disponible">{masi_svg(last)}</div><div class="chart-readout" aria-live="off">'
               + (f'{esc(last[-1][0])} · MASI {fmt(last[-1][1])} points' if last else 'Aucune série disponible')
               + '</div>' + explorer_footer() + '<script type="application/json" id="masi-data">'
               + json.dumps(points).replace('<','\\u003c') + '</script></div>'
               '<p class="fineprint">Le graphique représente les clôtures quotidiennes, pas la trajectoire intrajournalière. Les séances manquantes restent absentes. <a href="sources.html#marche">Origine des historiques et des observations</a>.</p></section>')
    breadth = overview.get('breadth') or {}
    up, down, flat = (breadth.get(k) for k in ('up','down','flat'))
    total = sum(v or 0 for v in (up,down,flat))
    bars = ''.join(f'<span class="breadth-{kind}" style="width:{(value or 0)*100/max(1,total):.2f}%"></span>'
                   for kind,value in (('up',up),('flat',flat),('down',down)))
    detail_only=(report.get('cross_source_volume_audit') or {}).get('publication_scope')=='validated_title_lines'
    official=overview.get('official_reference') or {}
    historical=report.get('volume_history_check') or {}
    if historical:
        reference=historical.get('reference')
        summary += ('<section class="panel"><h2>Historique des volumes</h2><p>'
            + (f'Export daté du {esc(reference["session"])} : {fmt(reference["transactions"],0)} transactions sur le marché central. '
               if reference else 'La séance courante n’est pas couverte par l’export historique. ')
            + 'Document fourni par l’utilisateur et relu ; les écarts fournisseurs sont conservés. '
              '<a href="historique-volumes.html">Consulter les séances, les marchés et les contrôles</a>.</p></section>')
    kpis = ''.join(f'<div class="kpi"><span>{name}</span><strong>{value}</strong></div>' for name,value in (
        ('Volume global · référence officielle · MDH' if official else 'Volume annoncé · non confirmé · MDH' if detail_only else 'Volume échangé · MDH', fmt(overview.get('turnover_mad')/1e6 if overview.get('turnover_mad') is not None else None)),
        ('Unités comptant · référence officielle' if official else 'Titres annoncés · non confirmés' if detail_only else 'Titres échangés',fmt(overview.get('shares'),0)),
        ('Contrats · référence officielle' if official else 'Transactions · date non attestée',fmt(official.get('contracts') if official else overview.get('transactions'),0)),
        ('Valeurs annoncées · non confirmées' if detail_only else 'Valeurs échangées',fmt(breadth.get('quoted'),0))))
    if overview.get('transactions_quality'):
        summary += (f'<section class="panel" data-market-counter-quality><h2>Compteurs et dates</h2>'
            f'<p>Compteur « transactions » du fournisseur : {fmt(overview.get("transactions_reported"),0)}. '
            'Sa date propre n’est pas attestée ; ce compteur est exclu du chiffre validé de séance.</p>'
            + (f'<p>Référence officielle du {esc(official.get("asof"))} : {fmt(official.get("contracts"),0)} contrats. '
               'Capture fournie par l’utilisateur et revue manuellement ; collecte officielle automatique non établie. '
               '<a href="https://www.casablanca-bourse.com/market-data/volume">Source officielle</a> · '
               '<a href="market-reference.json">Référence documentaire et méthode de vérification</a>.</p>' if official else '')+'</section>')
    summary += (f'<div class="kpis">{kpis}</div><section class="panel"><div class="section-heading"><h2>Participation du marché</h2>'
                f'<span class="panel-sub">Séance {esc(overview.get("asof"))} · lignes échangées recensées</span></div>'
                f'<div class="breadth-bar" aria-hidden="true">{bars}</div><div class="breadth-legend"><span class="gain">{fmt(up,0)} hausses</span>'
                f'<span>{fmt(flat,0)} inchangées</span><span class="loss">{fmt(down,0)} baisses</span></div></section>')
    audit = volume_reconciliation(report, overview)
    external = report.get('cross_source_volume_audit') or {}
    if external.get('publication_scope')=='validated_title_lines' and external.get('cross_source_verified'):
        total=(external.get('totals') or {}).get('retained_after') or {}
        summary += (f'<section class="panel banner" data-market-integrity="detail-only"><h2>{"Total global corroboré · détail à rapprocher" if official else "Total global non confirmé · titres recoupés séparément"}</h2>'
            f'<p>Les {esc(total.get("quoted"))} titres détaillés concordent entre deux fournisseurs : '
            f'{fmt(float(total.get("turnover_mad",0)))} MAD et {fmt(total.get("shares"),0)} actions.</p>'
            f'<p>Le total annoncé reste {fmt(overview.get("turnover_mad"))} MAD, {fmt(overview.get("shares"),0)} unités '
            f'et {fmt(breadth.get("quoted"),0)} lignes annoncées. '
            + ('Le montant global et la quantité sont corroborés par la référence officielle revue ; leur décomposition reste à rapprocher. ' if official else 'Ce total n’est pas recoupé. ')
            + 'Aucune ligne manquante n’est reconstituée.</p>'
            f'<p>Écarts annoncé moins détaillé : {fmt(overview.get("turnover_mad",0)-float(total.get("turnover_mad",0)))} MAD ; '
            f'{fmt(overview.get("shares",0)-total.get("shares",0),0)} unités ; {fmt(breadth.get("quoted",0)-total.get("quoted",0),0)} ligne(s).</p>'
            '<a href="market-integrity.json">Preuves et écarts</a> · <a href="error-memory.json">Journal des incidents</a></section>')
    elif external.get('cross_source_verified') and external.get('session') == overview.get('asof'):
        summary += (f'<section class="panel" data-market-integrity="verified"><h2>Volumes recoupés entre fournisseurs</h2>'
            f'<p>Deux fournisseurs recoupés · séance {esc(external.get("session"))}. '
            'Montants et cours vérifiés ligne par ligne, avec contrôle du total. '
            + ('Quantités également concordantes entre les deux fournisseurs.' if external.get('quantities_cross_source_verified') else 'Quantités non recoupées sur toutes les lignes.')
            + f'</p><p class="fineprint">Contrôle du {esc(external.get("observed_at"))}. L’indépendance des flux amont n’est pas attestée.</p>'
            '<a href="market-integrity.json">Détail du rapprochement</a> · <a href="error-memory.json">Journal des erreurs et corrections</a></section>')
    elif external.get('status') not in (None,'not_observed'):
        summary += (f'<div class="banner" data-market-integrity="degraded"><strong>Recoupement externe non confirmé</strong> · '
            f'séance {esc(external.get("session"))} · dernier contrôle {esc(external.get("observed_at"))}. '
            'Les données conservées ne sont pas présentées comme validées entre fournisseurs. '
            '<a href="market-integrity.json">Voir les réserves</a>.</div>')
    if audit['status'] == 'discrepancy':
        summary += (f'<div class="banner" data-volume-reconciliation="discrepancy">'
                    f'<strong>Écart de volume à vérifier · {esc(audit["asof"])}</strong> : '
                    f'synthèse de séance {fmt(audit["cdg_turnover_mad"]/1e6)} MDH ; '
                    f'somme des {audit["observed_lines"]} fiches de cette séance '
                    f'{fmt(audit["lines_turnover_mad"]/1e6)} MDH ; '
                    f'écart absolu {fmt(abs(audit["difference_mad"]))} DH. '
                    'Les relevés peuvent provenir de versions différentes. '
                    'Le montant de la synthèse reste affiché ; aucune correction des fiches n’est imposée.</div>')
    elif audit['status'] == 'matched':
        summary += (f'<p class="fineprint" data-volume-reconciliation="matched">'
                    f'Volume rapproché avec les {audit["observed_lines"]} fiches de la séance '
                    f'{esc(audit["asof"])} : {fmt(audit["lines_turnover_mad"]/1e6)} MDH. '
                    'Ce contrôle vérifie la concordance des montants, pas leur certification.</p>')
    elif audit['status'] == 'incomplete':
        summary += ('<p class="fineprint" data-volume-reconciliation="incomplete">'
                    'Rapprochement du volume incomplet : les fiches disponibles pour cette séance '
                    'ne permettent pas de valider le total de séance.</p>')
    sectors = overview.get('sectors') or []
    if sectors:
        summary += '<details class="panel"><summary>Indices sectoriels de la séance</summary><div class="sector-grid">'
        summary += ''.join(f'<div><span>{esc(s["libelle"].capitalize())}</span><strong class="{"gain" if s["variation_pct"]>0 else "loss" if s["variation_pct"]<0 else "muted"}">{fmt(s["variation_pct"])} %</strong></div>' for s in sectors)
        summary += '</div></details>'
    health = report.get('overview_health') or {}
    if health.get('result') == 'error':
        summary += '<div class="banner">Actualisation du MASI indisponible : dernière observation datée conservée.</div>'
    if not overview:
        summary += '<div class="banner">Bilan de séance indisponible : aucune valeur n’a été reconstituée.</div>'
    summary += f'<p class="fineprint"><a href="sources.html#marche">Sources du marché</a> · relevé {esc(overview.get("observed_at"))}. Les observations provisoires ne remplacent pas les clôtures de l’historique.</p>'
    return summary


def closing_summary(overview):
    if not overview:
        return 'Aucun bilan de clôture confirmé disponible.'
    index = overview.get('masi') or {}
    breadth = overview.get('breadth') or {}
    verb = 'est observé' if overview.get('status') == 'intraday' else 'clôture'
    lines = [f'Le MASI {verb} à {fmt(index.get("value"))} points ({fmt(index.get("change_pct"))} %), soit {fmt(index.get("variation_points"))} points par rapport à la clôture précédente.']
    official=overview.get('official_reference') or {}
    if official:
        lines.append(f'Référence officielle du {official["asof"]}, capture revue manuellement : {fmt(official["contracts"],0)} contrats. Le détail du périmètre reste à rapprocher.')
    if overview.get('low') is not None and overview.get('high') is not None:
        lines.append(f'Fourchette de séance : {fmt(overview["low"])} à {fmt(overview["high"])} points.')
    if breadth:
        lines.append(f'{fmt(breadth.get("down"),0)} valeurs en baisse, {fmt(breadth.get("up"),0)} en hausse et {fmt(breadth.get("flat"),0)} inchangées parmi les {fmt(breadth.get("quoted"),0)} valeurs échangées recensées.')
    if overview.get('turnover_mad') is not None:
        lines.append(f'Volume échangé : {fmt(overview["turnover_mad"]/1e6)} MDH.')
    return ' '.join(lines)
