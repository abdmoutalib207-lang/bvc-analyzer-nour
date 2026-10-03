"""Market-first HTML. Index history contains closes, not fabricated OHLCV."""
import html
import json


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
    last = points[-63:]
    change = index.get('change_pct')
    tone = 'gain' if change is not None and change > 0 else 'loss' if change is not None and change < 0 else 'muted'
    provisional = overview.get('status') == 'intraday'
    label = 'Point de séance provisoire' if provisional else 'Dernière clôture disponible'
    summary = (f'<section class="panel market-panel"><div class="focus-header"><div><span class="eyebrow">MASI · Casablanca</span>'
               f'<h2>{label} · {esc(overview.get("asof"))}</h2><div class="index-value">{fmt(index.get("value"))}<small>points</small></div></div>'
               f'<div class="index-change {tone}">{fmt(change)} %<small>{fmt(index.get("variation_points"))} points</small></div></div>'
               '<div class="market-stats">'
               f'<div><span>Clôture précédente</span><strong>{fmt(index.get("veille"))}</strong></div>'
               f'<div><span>Depuis le début de l’année</span><strong>{fmt(index.get("ytd_pct"))} %</strong></div>'
               f'<div><span>Plus haut de séance</span><strong>{fmt(overview.get("high"))}</strong></div>'
               f'<div><span>Plus bas de séance</span><strong>{fmt(overview.get("low"))}</strong></div></div>'
               '<div data-masi-chart><div class="chart-toolbar"><div class="periods" aria-label="Période MASI">'
               + ''.join(f'<button type="button" data-masi-period="{n}" aria-pressed="{str(n==63).lower()}">{title}</button>'
                         for n,title in ((21,'1M'),(63,'3M'),(252,'1A'),(0,'Tout')))
               + '</div><span class="panel-sub">Historique des clôtures · survolez ou touchez le graphique</span></div>'
               f'<div class="chart masi-chart">{masi_svg(last)}</div><div class="chart-readout" aria-live="polite">'
               + (f'{esc(last[-1][0])} · MASI {fmt(last[-1][1])} points' if last else 'Aucune série disponible')
               + '</div><script type="application/json" id="masi-data">'
               + json.dumps(points).replace('<','\\u003c') + '</script></div>'
               '<p class="fineprint">Le graphique représente les clôtures quotidiennes, pas la trajectoire intrajournalière. Les séances manquantes restent absentes. Historique initial repris de l’archive du moteur principal, dont certaines périodes viennent d’Investing.com ; nouvelles observations collectées directement par Nour auprès de CDG.</p></section>')
    breadth = overview.get('breadth') or {}
    up, down, flat = (breadth.get(k) for k in ('up','down','flat'))
    total = sum(v or 0 for v in (up,down,flat))
    bars = ''.join(f'<span class="breadth-{kind}" style="width:{(value or 0)*100/max(1,total):.2f}%"></span>'
                   for kind,value in (('up',up),('flat',flat),('down',down)))
    kpis = ''.join(f'<div class="kpi"><span>{name}</span><strong>{value}</strong></div>' for name,value in (
        ('Volume échangé · MDH', fmt(overview.get('turnover_mad')/1e6 if overview.get('turnover_mad') is not None else None)),
        ('Titres échangés',fmt(overview.get('shares'),0)),
        ('Transactions',fmt(overview.get('transactions'),0)),
        ('Valeurs échangées · source CDG',fmt(breadth.get('quoted'),0))))
    summary += (f'<div class="kpis">{kpis}</div><section class="panel"><div class="section-heading"><h2>Participation du marché</h2>'
                f'<span class="panel-sub">Séance {esc(overview.get("asof"))} · lignes échangées de la source CDG</span></div>'
                f'<div class="breadth-bar" aria-hidden="true">{bars}</div><div class="breadth-legend"><span class="gain">{fmt(up,0)} hausses</span>'
                f'<span>{fmt(flat,0)} inchangées</span><span class="loss">{fmt(down,0)} baisses</span></div></section>')
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
    summary += f'<p class="fineprint">Source : <a href="https://www.cdgcapitalbourse.ma/Bourse/market" target="_blank" rel="noopener">CDG Capital Bourse</a> · relevé {esc(overview.get("observed_at"))}. Les observations provisoires ne remplacent pas les clôtures de l’historique.</p>'
    return summary


def closing_summary(overview):
    if not overview:
        return 'Aucun bilan de clôture confirmé disponible.'
    index = overview.get('masi') or {}
    breadth = overview.get('breadth') or {}
    verb = 'est observé' if overview.get('status') == 'intraday' else 'clôture'
    lines = [f'Le MASI {verb} à {fmt(index.get("value"))} points ({fmt(index.get("change_pct"))} %), soit {fmt(index.get("variation_points"))} points par rapport à la clôture précédente.']
    if overview.get('low') is not None and overview.get('high') is not None:
        lines.append(f'Fourchette de séance : {fmt(overview["low"])} à {fmt(overview["high"])} points.')
    if breadth:
        lines.append(f'{fmt(breadth.get("down"),0)} valeurs en baisse, {fmt(breadth.get("up"),0)} en hausse et {fmt(breadth.get("flat"),0)} inchangées parmi les {fmt(breadth.get("quoted"),0)} valeurs échangées recensées par CDG.')
    if overview.get('turnover_mad') is not None:
        lines.append(f'Volume échangé : {fmt(overview["turnover_mad"]/1e6)} MDH.')
    return ' '.join(lines)
