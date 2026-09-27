"""Pre-render full market site: charts, rows and links work with scripts disabled."""
import csv
import html
import json
import re
from pathlib import Path


def esc(value):
    return html.escape(str(value if value is not None else "—"), quote=True)


def number(value, digits=2):
    if value is None:
        return "—"
    return f"{float(value):,.{digits}f}".replace(",", " ").replace(".", ",")


def quality(bar):
    try:
        if not float(bar["l"]) <= float(bar["c"]) <= float(bar["h"]):
            return "Clôture hors fourchette"
        if not float(bar["l"]) <= float(bar["o"]) <= float(bar["h"]):
            return "Ouverture hors fourchette"
    except (ValueError, TypeError, KeyError):
        return "Ligne invalide"
    return ""


def chart_data(bars):
    output = []
    for b in bars:
        if isinstance(b, (tuple, list)) and len(b) == 3:
            output.append(b)
        elif isinstance(b, dict) and b.get("c") is not None and not quality(b).startswith("Clôture"):
            output.append([b["d"], b["c"], b["v"]])
    return output


def svg_chart(bars):
    points_data = chart_data(bars)
    if not points_data:
        return '<div class="fallback" role="status">Historique de cours indisponible pour ce titre.</div>'
    close = [float(x[1]) for x in points_data]
    low, high = min(close), max(close)
    span = high - low or 1
    pts = " ".join(f"{53+820*i/max(1,len(close)-1):.1f},{219-193*(v-low)/span:.1f}" for i, v in enumerate(close))
    volume_max = max((float(x[2]) for x in points_data), default=1) or 1
    every = max(1, (len(points_data) + 99) // 100)
    volumes = "".join(
        f'<rect x="{53+820*i/max(1,len(close)-1):.1f}" y="{301-52*float(x[2])/volume_max:.1f}" width="{max(1,820/len(close)*every-1):.1f}" height="{52*float(x[2])/volume_max:.1f}" fill="#376754"/>'
        for i, x in enumerate(points_data) if i % every == 0
    )
    grid = "".join(f'<line x1="53" x2="873" y1="{27+i*64}" y2="{27+i*64}" stroke="#28434a"/><text x="4" y="{31+i*64}">{number(high-span*i/3, 0)}</text>' for i in range(4))
    return (f'<svg viewBox="0 0 900 330" role="img" aria-label="Cours de clôture de {len(close)} séances et volumes">'
            '<defs><linearGradient id="fade" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#a7df80" stop-opacity=".24"/><stop offset="1" stop-color="#a7df80" stop-opacity="0"/></linearGradient></defs>'
            f'{grid}<polygon points="53,219 {pts} 873,219" fill="url(#fade)"/><polyline points="{pts}" fill="none" stroke="#b4e283" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"/><line x1="53" x2="873" y1="246" y2="246" stroke="#28434a"/>{volumes}'
            f'<text x="53" y="322">{esc(points_data[0][0])}</text><text x="762" y="322">{esc(points_data[-1][0])}</text><text x="7" y="272">VOL.</text></svg>')


def shell(title, body, style, script):
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#08121b"><title>{esc(title)} · BVC Analyzer Nour</title><style>{style}</style></head><body>'
            f'{body}<script>{script}</script></body></html>')


def header(back, snapshot):
    prefix='../' if back.startswith('../') else ''
    return (f'<header class="top"><a class="brand" href="{back}"><span class="mark">N</span><span>BVC Analyzer Nour<small>MOTEUR INDÉPENDANT · SANS NLP</small></span></a>'
            f'<nav class="topnav" aria-label="Navigation"><a href="{prefix}index.html">Marché</a><a href="{prefix}briefing.html">Briefing</a><a href="{prefix}actualites.html">Actualités</a></nav>'
            f'<span class="topbadge">Dernières données · {esc(snapshot[:10])}</span></header>')


def graph(bars, label="1A"):
    data = chart_data(bars)
    default = data[-252:]
    if not data:
        return '<div id="plot" class="chart">' + svg_chart(default) + '</div>'
    controls = ''.join(f'<button type="button" data-period="{p}" aria-pressed="{str(p=="252").lower()}">{txt}</button>' for p, txt in [('21', '1M'), ('63', '3M'), ('252', label), ('all', 'Tout')])
    json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return (f'<div class="periods" role="group" aria-label="Période du graphique">{controls}</div><div class="chart" id="plot">{svg_chart(default)}</div>'
            f'<div id="chart-info" class="chart-info">{esc(default[0][0])} → {esc(default[-1][0])} · {len(default)} séances · {number(min(float(x[1]) for x in default))} à {number(max(float(x[1]) for x in default))} MAD</div>'
            f'<script type="application/json" id="history-data">{json_data}</script>')


def info_card(title, value, suffix=""):
    return f'<article class="kpi"><span>{esc(title)}</span><strong>{esc(value)}</strong>{(" <small>"+esc(suffix)+"</small>") if suffix else ""}</article>'


def recent_table(bars, count=40):
    rows = []
    for b in reversed(bars[-count:]):
        warning = quality(b)
        rows.append(f'<tr><td class="nowrap">{esc(b["d"])}</td><td>{number(b["o"])}</td><td>{number(b["h"])}</td><td>{number(b["l"])}</td><td><strong>{number(b["c"])}</strong></td><td>{number(b["v"],0)}</td><td class="warning">{esc(warning)}</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr><th>Séance</th><th>Ouverture</th><th>Haut</th><th>Bas</th><th>Clôture</th><th>Titres</th><th>Qualité</th></tr></thead><tbody>'
            + (''.join(rows) if rows else '<tr><td colspan="7">Historique absent dans l’archive source.</td></tr>')
            + '</tbody></table></div>')


def detail_page(item, record, fixture, style, script):
    symbol = item["symbol"]
    bars = record["candles"]
    first = bars[0]["d"] if bars else "—"
    last = bars[-1]["d"] if bars else "—"
    issues = item["quality"]["issues"]
    liq = item["liquidity"]
    cards = ''.join((
        info_card("Nombre de séances", str(len(bars))),
        info_card("Première séance disponible", first),
        info_card("Valeur échangée dernière séance", number(item["day_turnover_mad_actual"],0), "MAD réels"),
        info_card("Médiane valeur échangée 20 séances", number(liq["median_turnover_mad_estimated"],0) if liq["ready"] else "Non fiable", "MAD estimés"),
    ))
    caveat = ('<div class="banner">' + '<br>'.join(esc(reason) for reason in issues[:5]) + '</div>') if issues else ''
    trend = item["trend"]
    tech_cards = ''.join((
        info_card("Moyenne des 20 clôtures", number(trend["ma20"]) if trend["ready"] else "Non calculée", "MAD"),
        info_card("Variation sur 20 séances", (number(trend["change_20_sessions_pct"]) + " %") if trend["ready"] else "Non calculée"),
        info_card("Volatilité annualisée, 20 séances", (number(trend["realized_volatility_20d_pct"]) + " %") if trend["ready"] else "Non calculée"),
        info_card("Titres échangés dernière séance", number(item["day_shares"], 0)),
    ))
    calculated=item.get('fundamental') or {}
    technical=item.get('technical') or {}
    score=item.get('canonical_score') or {}
    tech_extended=''.join((info_card('RSI 14',number(technical.get('rsi14'))),
                           info_card('Moyenne 50 séances',number(technical.get('sma50')),'MAD'),
                           info_card('ATR 14',number(technical.get('atr14')),'MAD'),
                           info_card('Support 20 séances',number(technical.get('support20')),'MAD'),
                           info_card('Résistance 20 séances',number(technical.get('resistance20')),'MAD'),
                           info_card('Volume / médiane 20 séances',number(technical.get('volume_vs_median20')),'×')))
    fundamental_cards=''.join((info_card('Bénéfice par action',number(calculated.get('eps_mad')),'MAD'),
                               info_card('PER recalculé',number(calculated.get('pe'))),
                               info_card('P/B recalculé',number(calculated.get('pb'))),
                               info_card('ROE',number(calculated.get('roe_pct'))+' %' if calculated.get('roe_pct') is not None else '—'),
                               info_card('Croissance du CA',number(calculated.get('revenue_growth_pct'))+' %' if calculated.get('revenue_growth_pct') is not None else '—')))
    evidence=calculated.get('evidence') or {}
    doc=calculated.get('document_url')
    evidence_html=(f'<a href="{esc(doc)}" rel="noopener noreferrer" target="_blank">Rapport référencé · exercice {esc(calculated.get("exercise"))}</a> · '
                   + esc(', '.join(f'{k} p.{v["page"]}' for k,v in evidence.items()) or 'Aucun chiffre exploitable')
                   if doc else 'Aucun rapport sourcé disponible dans cette archive.')
    body = (header('../index.html', fixture["snapshot_updated"])
            + '<main><div class="hero"><a href="../index.html" class="muted">← Retour aux 80 valeurs</a>'
            + f'<div class="eyebrow" style="margin-top:20px">{esc(record.get("sector") or "Action cotée")} · {esc(symbol)}</div><h1>{esc(record["name"])}</h1>'
            + f'<p>Dernier cours disponible : <strong>{number(item["price"])} MAD</strong> au {esc(item["asof"])}. Source prix : {esc(item["price_source"])}. <span class="status {esc(item["decision"])}">{esc(item["decision"])}</span></p>'
            + f'<div class="stamp">Historique {esc(first)} → {esc(last)} · {len(bars)} séances · mis à jour après collecte validée</div></div>'
            + f'<section class="panel"><span class="eyebrow">Historique graphique</span><h2>{esc(symbol)} · clôtures et volumes</h2><p class="panel-sub">Courbe de clôture et volumes de titres. La plage « Tout » couvre exactement les séances disponibles ci-dessous.</p>{graph(bars)}</section>'
            + f'<div class="detail-grid">{cards}</div>{caveat}'
            + f'<section class="panel"><span class="eyebrow">Indicateurs calculés</span><h2>Tendance, momentum et risque</h2><div class="detail-grid">{tech_cards}{tech_extended}</div><p class="fineprint">Niveaux sur 20 séances précédentes, sans la séance du jour. Après reprise, seules les séances postérieures sont comparées.</p></section>'
            + f'<section class="panel"><span class="eyebrow">Score canonique · {esc(score.get("version"))}</span><h2>{number(score.get("value"),0) if score.get("value") is not None else "Non calculable"} / 100 · {esc(score.get("state"))}</h2><p>Couverture des facteurs : {number(score.get("coverage_pct"),0)} %. Le score est descriptif, jamais un ordre d’achat ou de vente. NLP : 0 %.</p><p class="fineprint">'+esc(' · '.join(f'{k} {v["points"]}/{v["weight"]}' for k,v in score.get('contributors',{}).items()) or 'Aucun facteur admissible')+'</p></section>'
            + f'<section class="panel"><span class="eyebrow">Fondamentaux</span><h2>Calculs et provenance</h2><div class="detail-grid">{fundamental_cards}</div><p class="fineprint">{evidence_html}</p><p class="fineprint">Les chiffres source sont extraits de rapports référencés de l’ancien projet. Les ratios sont recalculés par Nour, sous réserve de recoupement des pages indiquées. Le cours est celui daté en haut de cette fiche.</p></section>'
            + f'<section class="panel"><div class="section-heading"><div><span class="eyebrow">Données vérifiables</span><h2>Dernières {min(40,len(bars))} séances</h2></div><a class="btnlink" href="../historique/{esc(symbol)}.csv" download>Télécharger tout l’historique CSV</a></div>{recent_table(bars)}<p class="fineprint">Le CSV reprend {len(bars)} séances. Une ouverture hors de la fourchette haut/bas est signalée ; les volumes sont exprimés en nombre de titres. Cette série n’est pas une preuve de données intrajournalières ni de carnet.</p></section>'
            + '<section class="panel"><span class="eyebrow">Provenance</span><p class="fineprint">Archive initiale copiée en lecture seule du moteur précédent. ' + f'Commit source {esc(fixture["source_commit"])} ; snapshot {esc(fixture["snapshot_updated"])}. Ancien moteur : {esc(item["legacy_comparison"]["sig"])} / {esc(item["legacy_comparison"]["sigBvc"])}. Ces champs ne pilotent aucun calcul Nour.</p></section></main>'
            + '<footer>BVC Analyzer Nour · données et documents datés ; valider les sources avant toute décision financière.</footer>')
    return shell(f'{symbol} · {record["name"]}', body, style, script)


def home_page(fixture, report, style, script):
    items = {r["symbol"]: r for r in report["results"]}
    total_history = sum(bool(fixture["records"][s]["candles"]) for s in fixture["symbols"])
    counts = {x: sum(r["decision"] == x for r in report["results"]) for x in ("OBSERVABLE", "LIMITÉ", "INDISPONIBLE")}
    cards = ''.join((info_card("Titres suivis", str(len(items))),info_card("Historiques consultables", str(total_history)),info_card("Données observables", str(counts["OBSERVABLE"])),info_card("Données limitées / indisponibles", f'{counts["LIMITÉ"]} / {counts["INDISPONIBLE"]}')))
    masi = fixture.get("market", {}).get("masi", {})
    adir = items['ADI']
    rows = []
    for symbol in fixture["symbols"]:
        r, record = items[symbol], fixture["records"][symbol]
        search = f'{symbol} {record["name"]} {record.get("sector", "")}'.lower()
        search = ''.join(c for c in __import__('unicodedata').normalize('NFD', search) if __import__('unicodedata').category(c) != 'Mn')
        score=r.get('canonical_score',{})
        score_text = number(score.get('value'), 0) if score.get('value') is not None else '—'
        rows.append(f'<tr data-market-row data-search="{esc(search)}" data-sector="{esc(record.get("sector") or "Autre")}" data-score="{esc(score.get("value") if score.get("value") is not None else -1)}"><td><a href="titres/{esc(symbol)}.html">{esc(symbol)}</a></td><td>{esc(record["name"])}</td><td>{number(r["price"])} MAD</td><td class="nowrap">{esc(r["asof"])}</td><td>{len(record["candles"])}</td><td>{score_text}</td><td><span class="status {esc(r["decision"])}">{esc(r["decision"])}</span></td></tr>')
    sectors=sorted(set((fixture['records'][s].get('sector') or 'Autre') for s in fixture['symbols']))
    sector_options=''.join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in sectors)
    health=report.get('health') or {}
    body = (header('index.html',fixture["snapshot_updated"])
            + '<main><div class="hero"><span class="eyebrow">Nour / moteur de recherche de marché</span><h1>80 valeurs. <em>Un calcul traçable.</em></h1><p>Cours, historique, fondamentaux documentés, indicateurs et score canonique calculés dans Nour. Les actualités servent uniquement à la veille.</p>'
            + f'<div class="stamp">Données du {esc(fixture["snapshot_updated"][:10])} · rapport du {esc(report["analysis_date"])} · état collecte {esc(health.get("result") or "non configuré")} · {esc(health.get("message") or "")}</div><div class="primary-actions"><a class="btnlink" href="briefing.html">Lire le briefing de marché</a><a class="btnlink outline" href="actualites.html">Voir les actualités</a></div></div>'
            + f'<p class="panel-sub">MASI archivé : {number(masi.get("value"))} points · variation {number(masi.get("change_pct"))} % · état de marché {esc(fixture.get("market", {}).get("status"))}.</p>'
            + f'<div class="kpis">{cards}</div><section class="panel"><div class="focus-header"><div><span class="eyebrow">Valeur en vue · ADI</span><h2>Alliances Développement</h2><span class="status {esc(adir["decision"])}">{esc(adir["decision"])}</span></div><div class="price">{number(adir["price"])}<small>MAD</small></div></div>'
            + f'<p class="panel-sub">{len(fixture["records"]["ADI"]["candles"])} séances historiques ; clôture du {esc(adir["asof"])}. <a href="titres/ADI.html">Voir l’historique d’ADI →</a></p>{graph(fixture["records"]["ADI"]["candles"])}</section>'
            + '<section class="panel"><div class="section-heading"><div><span class="eyebrow">Univers complet</span><h2>Choisir une valeur</h2></div><div class="filters"><input id="search" class="search" type="search" aria-label="Rechercher une valeur" placeholder="Rechercher un code ou une société"><select id="sector" aria-label="Filtrer par secteur"><option value="">Tous les secteurs</option>'+sector_options+'</select><button type="button" id="sort-score">Trier par score</button></div></div>'
            + f'<div class="tablewrap"><table><thead><tr><th>Code</th><th>Société</th><th>Dernier cours</th><th>Date</th><th>Séances</th><th>Score</th><th>État des données</th></tr></thead><tbody id="market-body">{"".join(rows)}</tbody></table></div>'
            + '<p class="fineprint">Les états décrivent la disponibilité des données, jamais une recommandation. Un historique peut rester indisponible tant qu’aucune séance validée n’a été importée.</p></section>'
            + f'<div class="banner">Les calculs restent datés de leur dernière séance validée. Le score est descriptif et peut être non calculable. Source initiale : {esc(fixture["source_commit"])}.</div></main>'
            + '<footer>BVC Analyzer Nour · moteur indépendant · aucune écriture vers le moteur principal.</footer>')
    return shell('Marché et historiques', body, style, script)


def news_page(fixture, report, style, script):
    articles = report.get('news', [])
    rows = []
    for a in articles:
        title, url = esc(a.get('title')), esc(a.get('url'))
        tickers = ', '.join(a.get('tickers') or [])
        searchable = ' '.join((str(a.get('title') or ''), str(a.get('publisher') or ''), tickers)).lower()
        rows.append(f'<article class="news-item" data-news-row data-search="{esc(searchable)}" data-tier="{esc(a.get("tier"))}"><span class="eyebrow">{esc(a.get("publisher"))} · {esc(a.get("published_at","")[:10])} · {esc(a.get("tier"))}</span><h2><a href="{url}" target="_blank" rel="noopener noreferrer">{title} ↗</a></h2><p>{esc(a.get("status"))} · Titres associés : {esc(tickers or "non établis")}</p></article>')
    body = (header('index.html', fixture['snapshot_updated'])
            + '<main><div class="hero"><span class="eyebrow">Radar documentaire</span><h1>Actualités vérifiables</h1><p>Alertes et index de publications. Le rattachement au titre et la source sont visibles ; aucun article ne contribue au score.</p></div>'
            + '<section class="panel"><div class="filters"><input class="search" id="news-search" type="search" placeholder="Rechercher un titre ou une source" aria-label="Rechercher dans les actualités"><select id="news-tier" aria-label="Filtrer par niveau de source"><option value="">Toutes les sources</option><option value="S1">Index officiel AMMC</option><option value="S2">Veille secondaire</option></select></div><p class="fineprint">Une ligne S1 atteste la présence d’un document sur l’index AMMC ; son contenu financier n’est pas analysé automatiquement. Les autres lignes attendent une validation primaire.</p>'
            + '<div class="news-list">' + (''.join(rows) or '<p>Aucune actualité disponible.</p>') + '</div></section></main><footer>BVC Analyzer Nour · actualités réservées à la veille · NLP 0 %.</footer>')
    return shell('Actualités', body, style, script)


def briefing_page(fixture, briefing, style, script):
    focus = []
    for item in briefing['focus']:
        focus.append(f'<article class="brief-item"><div class="focus-header"><h3><a href="titres/{esc(item["symbol"])}.html">{esc(item["symbol"])} · {esc(item["name"])}</a></h3><strong>{number(item["price"])} MAD</strong></div><p>Clôture {esc(item["asof"])} · Score {number(item["score"],0) if item["score"] is not None else "non calculable"} · données {esc(item["data_status"])}</p><p>Support {number(item["support"])} · résistance {number(item["resistance"])} MAD · RSI {number(item["rsi"])} · activité {number(item["activity"])} ×</p><p>{esc(item["scenario"])}.</p></article>')
    headlines = ''.join(f'<li><a href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer">{esc(a["title"])} ↗</a> <span class="muted">{esc(a["publisher"])} · {esc(a["published_at"][:10])}</span></li>' for a in briefing.get('news', []))
    index = briefing.get('index') or {}
    index_line = (f'MASI {number(index.get("value"))} · variation {number(index.get("change_pct"))} %.' if index else esc(briefing.get('index_notice')))
    cov=briefing['coverage']
    body = (header('index.html', fixture['snapshot_updated'])
            + f'<main><div class="hero"><span class="eyebrow">Briefing de marché</span><h1>Point de séance</h1><p>Préparé pour le {esc(briefing["generated_for"])} à partir des dernières données validées. Une nouvelle publication de données régénère ce briefing.</p><div class="stamp">Dernière séance repérée : {esc(briefing["market_session"])} · {cov["quoted_session"]}/{cov["titles"]} valeurs cotées à cette date · {cov["observable"]} observables</div></div>'
            + f'<section class="panel"><h2>État du marché</h2><p>{index_line}</p><p>Statut de la source : {esc(briefing.get("market_status"))}. Le calcul conserve les dates par valeur ; il ne prolonge pas un cours absent sur une séance récente.</p></section>'
            + '<section class="panel"><h2>Valeurs à examiner</h2><p class="panel-sub">Niveaux techniques descriptifs établis sur les séances disponibles ; ils ne prédisent aucune trajectoire.</p><div class="brief-grid">'+''.join(focus)+'</div></section>'
            + '<section class="panel"><h2>Publications récentes</h2><ul class="headlines">'+(headlines or '<li>Aucune publication récente dans le flux indexé.</li>')+'</ul><a class="btnlink" href="actualites.html">Ouvrir tout le radar</a></section>'
            + f'<div class="banner">{esc(briefing["limitations"])} Les actualités ne contribuent jamais aux scores. Vérifier les documents d’origine avant décision.</div></main><footer>BVC Analyzer Nour · briefing reproductible depuis le snapshot publié.</footer>')
    return shell('Briefing', body, style, script)


def build_site(fixture, report, output, briefing=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "titres").mkdir(exist_ok=True)
    (output / "historique").mkdir(exist_ok=True)
    assets = Path(__file__).resolve().parents[1] / "web"
    style = (assets / "nour.css").read_text(encoding="utf-8")
    script = (assets / "nour.js").read_text(encoding="utf-8")
    (output / "index.html").write_text(home_page(fixture, report, style, script), encoding="utf-8")
    (output / "actualites.html").write_text(news_page(fixture, report, style, script), encoding="utf-8")
    if briefing is not None:
        (output / "briefing.html").write_text(briefing_page(fixture, briefing, style, script), encoding="utf-8")
    by_symbol = {r["symbol"]: r for r in report["results"]}
    for symbol in fixture["symbols"]:
        if not re.fullmatch(r"[A-Z0-9]{2,5}", symbol):
            raise ValueError(f"Unsafe symbol: {symbol!r}")
        rec = fixture["records"][symbol]
        (output / "titres" / f"{symbol}.html").write_text(detail_page(by_symbol[symbol], rec, fixture, style, script), encoding="utf-8")
        with (output / "historique" / f"{symbol}.csv").open("w", encoding="utf-8-sig", newline="") as out:
            writer = csv.writer(out, delimiter=";")
            writer.writerow(["Séance", "Ticker", "Ouverture", "Plus Haut", "Plus Bas", "Clôture", "Titres Échangés", "Contrôle OHLC"])
            for bar in rec["candles"]:
                writer.writerow([bar.get("d"), symbol, bar.get("o"), bar.get("h"), bar.get("l"), bar.get("c"), bar.get("v"), quality(bar)])
