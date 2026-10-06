"""Transparent research surfaces, with static summaries and interactive scenarios."""
import html
import json
from statistics import median
from .research import net_return


def esc(v):
    return html.escape(str(v if v is not None else '—'), quote=True)


def num(v, digits=2):
    return '—' if v is None else f'{v:,.{digits}f}'.replace(',', ' ').replace('.', ',')


def help_panel():
    """Native disclosure: the explanation also works without JavaScript."""
    return ('<details id="lab-help" class="lab-help">'
        '<summary id="lab-help-toggle" aria-label="Comprendre le laboratoire" aria-controls="lab-help-content">'
        '<span class="lab-help-icon" aria-hidden="true">?</span><span>Comment ça marche ?</span></summary>'
        '<div id="lab-help-content" class="lab-help-content">'
        '<h2>Le laboratoire, en langage simple</h2>'
        '<p><strong>Un banc d’essai du passé, pas un bouton « acheter ».</strong> '
        'La fiche décrit la situation actuelle d’un titre. Ici, on regarde ce qu’une règle précise aurait donné dans le passé.</p>'
        '<h3>Comment essayer ?</h3><ol>'
        '<li>Choisis un titre, par exemple ADI, puis une durée : <strong>5, 20 ou 60 séances</strong> de bourse.</li>'
        '<li>Renseigne tes frais : par exemple 1 % à l’achat et 1 % à la vente. '
        'Le « glissement » représente un prix d’exécution moins favorable que le prix observé.</li>'
        '<li>Lis les résultats historiques et les dates du tableau. Les filtres changent les cas étudiés, pas les cours ni les scores de Nour.</li></ol>'
        '<h3>Quelle règle est étudiée ?</h3>'
        '<p>À des dates espacées fixées à l’avance, le cours doit être au-dessus des moyennes des '
        '<strong>20 et 50 dernières séances</strong>. L’achat hypothétique se fait à la <strong>clôture suivante</strong>, '
        'puis la vente après la durée choisie. Les cas dont les données nécessaires manquent sont écartés.</p>'
        '<h3>Que veulent dire les chiffres ?</h3><dl>'
        '<dt>Observations</dt><dd>Le nombre de cas historiques étudiés. Avec moins de 30 cas, l’échantillon est insuffisant pour interpréter une fréquence.</dd>'
        '<dt>Fréquence positive</dt><dd>La proportion de cas terminés en gain après les frais choisis. '
        '<strong>Exemple fictif : 60 % = 60 cas sur 100 dans le passé. Cela ne prédit pas demain.</strong></dd>'
        '<dt>Médiane nette</dt><dd>Le résultat du milieu après les frais choisis : la moitié des cas fait mieux, l’autre moins bien.</dd>'
        '<dt>Percentiles 10 / 90</dt><dd>Deux repères entre lesquels se situent environ 80 % des résultats observés. Ce ne sont pas des limites de perte ou de gain garanties.</dd>'
        '<dt>Écart au MASI</dt><dd>Le titre a-t-il fait mieux ou moins bien que l’indice sur les mêmes périodes ? '
        'Attention : le titre est comparé après les frais choisis, le MASI sans frais.</dd></dl>'
        '<p>Le filtre « MASI au signal » sépare les cas où l’indice était au-dessus ou sous sa moyenne des 200 dernières séances. '
        'Plus bas, le tableau de risque montre quels titres bougent fortement et suivent le MASI.</p>'
        '<p class="lab-help-warning"><strong>Ce qui n’est pas testé :</strong> l’achat sur des supports précis, '
        'les dividendes, la fiscalité et une exécution réelle des ordres. '
        'Les notes de Nour sont archivées pour être évaluées plus tard : leur efficacité n’est pas encore démontrée.</p>'
        '<p class="fineprint">Reclique sur le « ? » pour refermer cette explication.</p>'
        '<button type="button" id="lab-help-close" class="btnlink outline" hidden>Fermer l’explication</button>'
        '</div></details>')


def panels(item):
    r = item.get('market_risk', {})
    cards = ''.join(f'<div class="metric"><span>{label}</span><strong>{num(r.get(key))}{unit}</strong></div>' for key,label,unit in (
        ('beta', 'Bêta vs MASI', ''), ('correlation', 'Corrélation vs MASI', ''),
        ('volatility_pct', 'Volatilité annualisée du titre', ' %'),
        ('masi_volatility_pct', 'Volatilité MASI appariée', ' %'),
        ('drawdown_pct', 'Baisse maximale sur la fenêtre', ' %'),
        ('relative_return_pp', 'Écart de rendement au MASI', ' points')))
    comparison = item.get('sector_comparison', {})
    names = {'pe': 'PER', 'pb': 'P/B', 'roe_pct': 'ROE (%)'}
    rows = ''.join(f'<tr><td>{names[k]}</td><td>{num(m.get("value"))}</td><td>{num(m.get("median"))}</td>'
                  f'<td>{num(m.get("percentile"),1)}</td><td>{m.get("other_peers",0)}</td><td>{esc(", ".join(m.get("symbols",[])))}</td></tr>'
                  for k,m in comparison.get('metrics', {}).items())
    return ('<section class="panel"><span class="eyebrow">Référence de marché</span><h2>Le risque face au MASI</h2>'
        f'<p>{r.get("paired_returns",0)} rendements quotidiens appariés sur {r.get("market_calendar_sessions",0)} séances de référence. Minimum : 60. '
        f'{esc(r.get("first"))} → {esc(r.get("last"))}.</p><div class="research-metrics">{cards}</div>'
        '<p class="fineprint">La baisse maximale et l’écart de rendement exigent une fenêtre complète. '
        f'{esc(r.get("note"))}</p><a href="../recherche.html">Explorer les tendances après frais →</a></section>'
        '<section class="panel"><span class="eyebrow">Comparaison comptable stricte</span><h2>Au sein du secteur</h2>'
        f'<p>{esc(comparison.get("sector"))} · exercice {esc(comparison.get("exercise"))} · {esc(comparison.get("scope"))} · {esc(comparison.get("standard"))}</p>'
        '<div class="tablewrap"><table><thead><tr><th>Ratio</th><th>Ce titre</th><th>Médiane des autres</th><th>Percentile / 100</th><th>Autres titres admissibles</th><th>Codes</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div><p class="fineprint">{esc(comparison.get("note"))} Une case vide reste indisponible.</p></section>')


def teaser(report):
    r = report.get('research', {})
    risk_count = sum(x.get('market_risk',{}).get('status') == 'available' for x in report['results'])
    return ('<section class="panel research-teaser"><div class="section-heading"><div><span class="eyebrow">Laboratoire statistique · v1</span>'
        '<h2>Comparer. Mesurer. Vérifier.</h2>'
        f'<p>{r.get("masi_sessions",0)} séances MASI · {risk_count} titres avec risque apparié · scénarios après frais et périodes séparées.</p>'
        '</div><a class="btnlink" href="recherche.html">Explorer le laboratoire →</a></div>'
        '<p class="fineprint">Étude historique exploratoire. Scores archivés dès leur première observation ; aucune performance prédictive revendiquée.</p></section>')


def page_body(fixture, report):
    r = report.get('research', {'rows': [], 'audit': []})
    data = r.get('rows', [])
    default = [x for x in data if x['symbol'] == 'MASI' and x['horizon'] == 20]
    net = [net_return(x['entry'],x['exit'],1,1) for x in default]
    static = (f'{len(net)} observations · rendement net médian {num(median(net) if net else None)} % · '
              f'fréquence positive {num(100*sum(x>0 for x in net)/len(net) if net else None,1)} %')
    options = '<option value="MASI">MASI · référence</option>'+''.join(
        f'<option value="{esc(s)}">{esc(s)} · {esc(fixture["records"][s]["name"])}</option>' for s in fixture['symbols'])
    payload = json.dumps(r,ensure_ascii=False,separators=(',', ':')).replace('<','\\u003c')
    limits = ''.join(f'<li>{esc(x)}</li>' for x in r.get('limitations', []))
    archive = report.get('score_archive', {})
    risks = ''.join(f'<tr><td><a href="titres/{esc(x["symbol"])}.html">{esc(x["symbol"])}</a></td>'
                    f'<td>{x.get("market_risk",{}).get("paired_returns",0)}</td>'
                    + ''.join(f'<td>{num(x.get("market_risk",{}).get(k))}</td>' for k in ('beta','correlation','volatility_pct','drawdown_pct'))+'</tr>'
                    for x in report['results'])
    return ('<main id="research-lab"><div class="hero research-hero"><span class="eyebrow">BVC Analyzer Nour · laboratoire historique</span>'
        '<h1>La tendance <em>à l’épreuve des données.</em></h1>'
        + help_panel() + '<p>Comparez un titre au MASI, observez le risque et faites varier les frais. Chaque résultat renvoie aux dates et aux prix qui l’ont produit.</p>'
        f'<div class="stamp">MASI : {esc(r.get("masi_first"))} → {esc(r.get("masi_last"))} · {r.get("masi_sessions",0)} séances · {r.get("universe_size",0)} titres</div></div>'
        '<section class="panel"><span class="eyebrow">Scénario interactif · prix seuls</span><h2>Tendances et coûts</h2>'
        '<div class="research-controls">'
        f'<label>Instrument<select id="lab-symbol">{options}</select></label>'
        '<label>Horizon<select id="lab-horizon"><option value="5">5 séances</option><option value="20" selected>20 séances</option><option value="60">60 séances</option></select></label>'
        '<label>Période<select id="lab-period"><option value="all">Toute l’archive</option><option value="2023-2024">2023–2024</option><option value="2025+">Depuis 2025</option></select></label>'
        '<label>MASI au signal<select id="lab-regime"><option value="all">Tous les régimes</option><option value="above">Au-dessus de MM200</option><option value="below">Sous MM200</option></select></label>'
        '<label>Frais achat (%)<input id="lab-buy" type="number" min="0" max="10" step="0.1" value="1"></label>'
        '<label>Frais vente (%)<input id="lab-sell" type="number" min="0" max="10" step="0.1" value="1"></label>'
        '<label>Glissement par côté (%)<input id="lab-slip" type="number" min="0" max="10" step="0.1" value="0"></label></div>'
        f'<p id="lab-status" role="status" aria-live="polite">MASI · 20 séances · achat 1 %, vente 1 %. {static}. Les contrôles nécessitent JavaScript.</p>'
        '<div id="lab-metrics" class="research-metrics"></div><div id="lab-distribution" class="research-distribution"></div>'
        '<p id="lab-audit" class="fineprint"></p><div id="lab-periods" class="tablewrap"></div>'
        '<div class="section-heading"><h3>Observations chronologiques</h3><a class="btnlink outline" href="recherche.csv" download>Toutes les observations · CSV</a></div>'
        '<div class="tablewrap"><table><thead><tr><th>Signal</th><th>Entrée</th><th>Sortie</th><th>Brut (%)</th><th>Net scénario (%)</th><th>MASI brut (%)</th><th>Écart net / MASI brut (points)</th></tr></thead><tbody id="lab-rows"></tbody></table></div>'
        '<p class="fineprint">Les 60 dernières observations filtrées sont affichées. L’export comprend l’archive entière, les prix, les régimes et les horizons. '
        'Le MASI brut est une référence d’indice, sans frais. Les statistiques de périodes regroupent des observations, pas un portefeuille ni un rendement annualisé.</p></section>'
        '<section class="panel"><span class="eyebrow">Méthode ouverte</span><h2>Ce qui est testé, ce qui reste à prouver</h2>'
        f'<p>{esc(r.get("protocol"))}</p><ul>{limits}</ul>'
        '<p>Net = sortie × (1 − frais vente − glissement) / [entrée × (1 + frais achat + glissement)] − 1. '
        'Moins de 30 observations : échantillon insuffisant pour interpréter une fréquence. Aucun seuil n’a été ajusté sur les résultats de cette page.</p>'
        '<a href="recherche.json" download>Protocole, exclusions et observations · JSON</a></section>'
        '<section class="panel"><span class="eyebrow">Suivi prospectif</span><h2>Le score, observé avant son résultat</h2>'
        f'<p>{archive.get("daily_snapshots",0)} archives quotidiennes · première date {esc(archive.get("first_day"))}. {esc(archive.get("note"))}</p>'
        '<p>Évaluation en attente : aucune performance future du score encore validée.</p>'
        '<p class="fineprint">Chaque archive conserve l’heure réelle, le score et sa version, les entrées comptables et techniques et leur empreinte SHA-256. '
        'Un historique de cours de trois ans n’est pas un historique de scores publiés de trois ans.</p></section>'
        '<section class="panel"><span class="eyebrow">Risque transversal · cours seuls</span><h2>Les titres face au MASI</h2>'
        '<div class="tablewrap"><table><thead><tr><th>Code</th><th>Rendements appariés</th><th>Bêta</th><th>Corrélation</th><th>Volatilité annualisée (%)</th><th>Baisse maximale (%)</th></tr></thead>'
        f'<tbody>{risks}</tbody></table></div><p class="fineprint">253 séances MASI maximum, au moins 60 rendements appariés. Baisse maximale uniquement si la fenêtre est complète. Aucun dividende ni interpolation.</p></section>'
        f'<script type="application/json" id="lab-data">{payload}</script></main>'
        '<footer>Nour · données datées · statistiques historiques · sans NLP décisionnel ni prédiction.</footer>')
