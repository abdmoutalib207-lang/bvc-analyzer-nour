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
    return (f'<header class="top"><a class="brand" href="{back}"><span class="mark">N</span><span>BVC Analyzer Nour<small>LABORATOIRE INDÉPENDANT</small></span></a><span class="topbadge">Archive · {esc(snapshot[:10])}</span></header>')


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
    fundamentals = record.get("fundamentals") or {}
    fundamental_text = (f'PER {number(fundamentals.get("per"))} · P/B {number(fundamentals.get("pb"))} · Rendement affiché {number(fundamentals.get("dividend_yield_pct"))} %. '
                        f'Source déclarée : {esc(fundamentals.get("source"))} ; arrêté : {esc(fundamentals.get("asof"))}. Ces valeurs reprises du moteur principal ne sont pas recalculées par Nour.')
    body = (header('../index.html', fixture["snapshot_updated"])
            + '<main><div class="hero"><a href="../index.html" class="muted">← Retour aux 80 valeurs</a>'
            + f'<div class="eyebrow" style="margin-top:20px">{esc(record.get("sector") or "Action cotée")} · {esc(symbol)}</div><h1>{esc(record["name"])}</h1>'
            + f'<p>Dernier cours disponible : <strong>{number(item["price"])} MAD</strong> au {esc(item["asof"])}. Source prix : {esc(item["price_source"])}. <span class="status {esc(item["decision"])}">{esc(item["decision"])}</span></p>'
            + f'<div class="stamp">Historique {esc(first)} → {esc(last)} · {len(bars)} séances · archive figée</div></div>'
            + f'<section class="panel"><span class="eyebrow">Historique graphique</span><h2>{esc(symbol)} · clôtures et volumes</h2><p class="panel-sub">Courbe de clôture et volumes de titres. La plage « Tout » couvre exactement les séances disponibles ci-dessous.</p>{graph(bars)}</section>'
            + f'<div class="detail-grid">{cards}</div>{caveat}'
            + f'<section class="panel"><span class="eyebrow">Mesures descriptives</span><h2>Tendance et contexte</h2><div class="detail-grid">{tech_cards}</div><p class="fineprint">{fundamental_text}</p></section>'
            + f'<section class="panel"><div class="section-heading"><div><span class="eyebrow">Données vérifiables</span><h2>Dernières {min(40,len(bars))} séances</h2></div><a class="btnlink" href="../historique/{esc(symbol)}.csv" download>Télécharger tout l’historique CSV</a></div>{recent_table(bars)}<p class="fineprint">Le CSV reprend {len(bars)} séances. Une ouverture hors de la fourchette haut/bas est signalée ; les volumes sont exprimés en nombre de titres. Cette série n’est pas une preuve de données intrajournalières ni de carnet.</p></section>'
            + '<section class="panel"><span class="eyebrow">Provenance</span><p class="fineprint">Données reprises d’une archive du projet principal, en lecture seule. ' + f'Commit source {esc(fixture["source_commit"])} ; snapshot {esc(fixture["snapshot_updated"])}. Ancien moteur : {esc(item["legacy_comparison"]["sig"])} / {esc(item["legacy_comparison"]["sigBvc"])}. Ces deux anciens champs ne pilotent aucun calcul Nour.</p></section></main>'
            + '<footer>BVC Analyzer Nour · prototype autonome ; source historique à vérifier avant toute utilisation financière.</footer>')
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
        rows.append(f'<tr data-market-row data-search="{esc(search)}"><td><a href="titres/{esc(symbol)}.html">{esc(symbol)}</a></td><td>{esc(record["name"])}</td><td>{number(r["price"])} MAD</td><td class="nowrap">{esc(r["asof"])}</td><td>{len(record["candles"])}</td><td><span class="status {esc(r["decision"])}">{esc(r["decision"])}</span></td></tr>')
    body = (header('index.html',fixture["snapshot_updated"])
            + '<main><div class="hero"><span class="eyebrow">Nour / vue de marché</span><h1>80 valeurs. <em>Un historique visible.</em></h1><p>Un nouveau dépôt de recherche fondé sur les données archivées du moteur principal. Chaque titre possède sa page, une courbe de clôtures et de volumes, ses dernières séances et son CSV complet.</p>'
            + f'<div class="stamp">Arrêté du {esc(fixture["snapshot_updated"][:10])} · consultation au {esc(report["analysis_date"])} · aucun cours en direct</div></div>'
            + f'<p class="panel-sub">MASI archivé : {number(masi.get("value"))} points · variation {number(masi.get("change_pct"))} % · état de marché {esc(fixture.get("market", {}).get("status"))}.</p>'
            + f'<div class="kpis">{cards}</div><section class="panel"><div class="focus-header"><div><span class="eyebrow">Valeur en vue · ADI</span><h2>Alliances Développement</h2><span class="status {esc(adir["decision"])}">{esc(adir["decision"])}</span></div><div class="price">{number(adir["price"])}<small>MAD</small></div></div>'
            + f'<p class="panel-sub">{len(fixture["records"]["ADI"]["candles"])} séances historiques ; clôture du {esc(adir["asof"])}. <a href="titres/ADI.html">Voir l’historique d’ADI →</a></p>{graph(fixture["records"]["ADI"]["candles"])}</section>'
            + '<section class="panel"><div class="section-heading"><div><span class="eyebrow">Univers complet</span><h2>Choisir une valeur</h2></div><input id="search" class="search" type="search" aria-label="Rechercher une valeur" placeholder="Rechercher un code ou une société"></div>'
            + f'<div class="tablewrap"><table><thead><tr><th>Code</th><th>Société</th><th>Dernier cours</th><th>Date</th><th>Séances</th><th>État des données</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            + '<p class="fineprint">Les états décrivent la disponibilité des données, jamais une recommandation. DIS et DLM n’ont pas de série de cours dans cette archive ; leurs pages expliquent cette limite.</p></section>'
            + f'<div class="banner">Archive figée du 25/09/2026 : ce site ne se met pas à jour automatiquement. Les données manquantes ou périmées sont affichées comme telles. Commit source : {esc(fixture["source_commit"])}.</div></main>'
            + '<footer>BVC Analyzer Nour · prototype indépendant · aucune connexion d’écriture vers le moteur public.</footer>')
    return shell('Marché et historiques', body, style, script)


def build_site(fixture, report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "titres").mkdir(exist_ok=True)
    (output / "historique").mkdir(exist_ok=True)
    assets = Path(__file__).resolve().parents[1] / "web"
    style = (assets / "nour.css").read_text(encoding="utf-8")
    script = (assets / "nour.js").read_text(encoding="utf-8")
    (output / "index.html").write_text(home_page(fixture, report, style, script), encoding="utf-8")
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
