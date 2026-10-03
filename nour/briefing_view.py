"""Readable, linked market briefing; every explanation exposes its inputs."""
import html
from .market_view import fmt
from .editorial import numeric


def esc(value):
    return html.escape(str(value if value is not None else '—'),quote=True)


def paragraphs(items):
    return ''.join(f'<p>{esc(p)}</p>' for p in items)


def publication(a):
    primary=a.get('tier')=='S1'
    title=a.get('title','');lower=title.lower()
    angle=('À vérifier dans les comptes : croissance, marge, résultat, dette et trésorerie ; le titre du document ne fournit pas ces chiffres.' if 'résultat' in lower else
           'À vérifier : conditions, financement, calendrier et autorisations ; une signature n’est pas une opération finalisée.' if 'acquisition' in lower or 'accord' in lower else
           'À vérifier : date d’effet, périmètre et conséquences opérationnelles dans le document lié.')
    return (f'<article class="publication"><h3><a href="{esc(a.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(title)} ↗</a></h3>'
            f'<p class="fineprint">{esc(a.get("publisher"))} · {esc(a.get("published_at","")[:10])} · {"Document officiel repéré" if primary else "Alerte de presse à recouper"}</p>'
            f'<p>{esc(angle)}</p></article>')


def fundamentals_reading(f):
    if not f.get('document_url'):
        return '<p>Aucun jeu de faits financiers référencé pour ce titre. Aucune appréciation de valorisation n’est attribuée.</p>'
    metrics=[]
    for key,label,unit in [('eps_mad','BPA',' MAD'),('pe','PER',' ×'),('pb','P/B',' ×'),('roe_pct','ROE',' %'),('revenue_growth_pct','Croissance du CA',' %')]:
        if numeric(f.get(key)):metrics.append(f'{label} {fmt(f[key])}{unit}')
    evidence=f.get('evidence') or {}
    pages=sorted(set(x['page'] for x in evidence.values() if isinstance(x.get('page'),int)))
    return (f'<p>Base fondamentale référencée : exercice {esc(f.get("exercise"))}. '+esc(' ; '.join(metrics) or 'Ratios non calculables à partir des faits disponibles.')+'.</p>'
            f'<p class="fineprint"><a href="{esc(f["document_url"])}" target="_blank" rel="noopener noreferrer">Rapport source ↗</a> · pages {esc(", ".join(map(str,pages)) or "non renseignées")}. '
            'Chiffres hérités à recouper ; les multiples utilisent le cours daté de la fiche. Cette base historique ne remplace pas les derniers résultats semestriels et ne prouve pas qu’un titre est bon marché.</p>')


def focus_article(item, intraday_html=''):
    reading=item.get('reading') or {};change=reading.get('change_pct');relative=reading.get('relative_masi_pp')
    tone='negative' if change is not None and change<0 else 'positive' if change is not None and change>0 else 'neutral'
    change_text=f'{fmt(change)} %' if change is not None else 'Variation comparable indisponible'
    dated=f'Clôture {esc(item["asof"])} · {esc(reading.get("source"))} · données {esc(item["data_status"])}'
    metrics=(f'Support de référence {fmt(item["support"])} · borne haute {fmt(item["resistance"])} MAD · RSI {fmt(item["rsi"])} · activité {fmt(item["activity"])} ×')
    score=f'{fmt(item["score"],0)}/100' if item['score'] is not None else 'non calculable'
    news=''.join(publication(a) for a in item.get('publications',[]))
    return (f'<article class="brief-item editorial-title" id="valeur-{esc(item["symbol"])}"><div class="focus-header">'
            f'<h3><a href="titres/{esc(item["symbol"])}.html">{esc(item["symbol"])} · {esc(item["name"])}</a></h3><strong>{fmt(item["price"])} MAD</strong></div>'
            f'<p><span class="pill tone-{tone}">{change_text}</span></p><p class="fineprint">{dated}</p>'
            +paragraphs(reading.get('paragraphs') or [item['scenario']])
            +f'<p class="brief-levels">{esc(metrics)}</p><details><summary>Fondamentaux, sources et score descriptif</summary>'
            +fundamentals_reading(reading.get('fundamental') or {})
            +f'<p><strong>Points sectoriels à examiner :</strong> {esc(reading.get("checkpoint"))}</p>'
            +f'<p class="fineprint">Score canonique {esc(score)} · {esc(item["score_state"])}. Il décrit les facteurs renseignés ; il n’est ni une recommandation ni une probabilité.</p></details>'
            +news+intraday_html+'</article>')


def render_editorial(briefing, intraday_renderer):
    e=briefing.get('editorial') or {};idx=briefing.get('index') or {}
    source=(f'<p class="fineprint">Source marché : <a href="{esc(e["source_url"])}" target="_blank" rel="noopener noreferrer">{esc(e.get("source"))} ↗</a> · relevé {esc(e.get("observed_at"))}.</p>' if e.get('source_url') else '<p class="fineprint">Source MASI non confirmée pour cette séance.</p>')
    essential=paragraphs(e.get('paragraphs') or [briefing.get('index_notice') or 'Synthèse de marché indisponible.'])
    sections=f'<section class="panel briefing-section" id="essentiel"><span class="eyebrow">Lecture de séance</span><h2>L’essentiel</h2>{essential}{source}</section>'
    ranking=[]
    for label,key in [('Plus fortes hausses comparables','leaders'),('Plus fortes baisses comparables','laggards')]:
        entries=[r for r in e.get(key,[]) if r['change_pct']>0] if key=='leaders' else [r for r in e.get(key,[]) if r['change_pct']<0]
        ranking.append(f'<div><h3>{label}</h3><ul>'+(''.join(f'<li><a href="titres/{esc(r["symbol"])}.html">{esc(r["symbol"])}</a> · {fmt(r["change_pct"])} %</li>' for r in entries) or '<li>Aucune valeur comparable dans cette catégorie.</li>')+'</ul></div>')
    sections+='<section class="panel briefing-section" id="secteurs"><h2>Largeur, secteurs et valeurs motrices</h2>'+paragraphs(e.get('sector_paragraphs',[]))+f'<div class="brief-ranking">{"".join(ranking)}</div><p class="fineprint">Classements sur {esc(e.get("ranking_coverage",0))} valeurs comparables à la même séance précédente ({esc(e.get("previous_session"))}), parmi les données acceptées par Nour ; ils ne constituent pas le palmarès exhaustif de la Bourse.</p></section>'
    flows=e.get('flows',[])
    flowlist='<ul>'+''.join(f'<li><a href="titres/{esc(x["symbol"])}.html">{esc(x["symbol"])}</a> : {fmt(x["amount"]/1e6)} MDH</li>' for x in flows)+'</ul>' if flows else '<p>Volumes monétaires réels par titre non disponibles sur cette séance.</p>'
    sections+=f'<section class="panel briefing-section" id="flux"><h2>Liquidité et activité</h2><p>Principaux volumes monétaires renseignés dans la couverture Nour pour cette clôture :</p>{flowlist}<p>Une forte activité ne suffit pas à conclure à du Smart Money. Sans carnet, détail des transactions et persistance multi-séances, l’absorption, la distribution et l’identité des intervenants ne sont pas établies.</p><p class="fineprint">Les montants ci-dessus sont les volumes MAD collectés. Les médianes historiques dans les fiches restent des estimations clôture × quantité.</p></section>'
    focus=''.join(focus_article(item,intraday_renderer(item)) for item in briefing.get('focus',[]))
    sections+='<section class="panel briefing-section" id="valeurs"><h2>Valeurs à surveiller</h2><p class="panel-sub">Suivi public commun à tous les lecteurs ; aucune position personnelle n’entre dans le briefing.</p><div class="editorial-focus">'+(focus or '<p>Aucune valeur du suivi n’a une clôture confirmée à cette date.</p>')+'</div></section>'
    cov=briefing.get('fundamental_coverage') or {}
    official=[a for a in briefing.get('news',[]) if a.get('tier')=='S1']
    sections+=f'<section class="panel briefing-section" id="fondamentaux"><h2>Fondamentaux et catalyseurs publiés</h2><p>{esc(cov.get("referenced",0))}/{esc(cov.get("titles",0))} titres possèdent une base de faits financiers référencés. Les ratios historiques et les annonces récentes sont distingués.</p><p>Les dépôts suivants ont été repérés dans le flux officiel. Leur existence est documentée ; leur contenu chiffré n’est pas encore extrait ni validé par ce briefing. Ils ne sont donc pas présentés comme une croissance acquise ou un catalyseur haussier.</p>'+(''.join(publication(a) for a in official[:10]) or '<p>Aucun dépôt récent retenu pour cette période.</p>')+'</section>'
    context=briefing.get('context_news') or []
    sections+='<section class="panel briefing-section" id="macro"><h2>Macroéconomie et international</h2>'+(''.join(publication(a) for a in context[:4]) if context else '<p>Aucune donnée macroéconomique ou internationale récente n’est confirmée dans le flux chargé. Le briefing n’attribue donc aucun prix au pétrole ni aucune décision à BAM ou à la Fed.</p>')+'<p><strong>Canaux à surveiller :</strong> taux et coût de financement ; énergie et transport ; change pour les importateurs ; prix des métaux pour les minières. Ce sont des facteurs de sensibilité, pas des événements supposés survenus aujourd’hui.</p></section>'
    scenarios=''.join(f'<article class="scenario-card"><h3>{esc(s["name"])}</h3><p><strong>Condition :</strong> {esc(s["condition"])}</p><p>{esc(s["reading"])}</p></article>' for s in e.get('scenarios',[]))
    sections+='<section class="panel briefing-section" id="scenarios"><h2>Scénarios pour la prochaine séance</h2><p class="panel-sub">Scénarios conditionnels, sans probabilités faute de modèle calibré hors échantillon. Les bornes MASI reposent sur les 20 clôtures antérieures disponibles, sans inclure la séance analysée.</p><div class="brief-grid">'+(scenarios or '<p>Clôture ou profondeur historique insuffisante pour fixer des bornes fiables.</p>')+'</div></section>'
    sections+='<section class="panel briefing-section" id="vigilance"><h2>Points de vigilance</h2><ul>'+''.join(f'<li>{esc(x)}</li>' for x in e.get('vigilance',[]))+'</ul><p>Comparer les confirmations de cours, la largeur de marché et la liquidité. Une surperformance isolée ou un RSI faible ne suffit pas à confirmer un retournement.</p></section>'
    secondary=[a for a in briefing.get('news',[]) if a.get('tier')!='S1']
    if secondary: sections+='<details class="panel"><summary>Radar de presse — alertes à recouper</summary>'+''.join(publication(a) for a in secondary[:6])+'</details>'
    return sections


def briefing_text(briefing):
    """Shareable text from the exact rendered edition, with dates and links."""
    from html.parser import HTMLParser
    class Plain(HTMLParser):
        def __init__(self):super().__init__();self.parts=[]
        def handle_starttag(self,tag,attrs):
            if tag=='a':
                url=dict(attrs).get('href','')
                if url.startswith('https://'):self.parts.append(f' [{url}] ')
        def handle_endtag(self,tag):
            if tag in ('p','h2','h3','li','summary'):self.parts.append('\n\n')
        def handle_data(self,text):self.parts.append(text)
    p=Plain();p.feed(render_editorial(briefing,lambda item:''))
    return f'{briefing.get("title","Briefing")} — séance {briefing.get("market_session")}\nPréparé le {briefing["generated_for"]}\n\n'+''.join(p.parts)
