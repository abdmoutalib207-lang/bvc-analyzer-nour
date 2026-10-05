"""Static, accessible macro tables and metadata-only geography/category radar."""
import html
from .macro import mode_label
from .macro_news import CATEGORIES, SCOPES


def esc(value):
    return html.escape(str(value if value is not None else '—'),quote=True)


def number(value, digits=2):
    return '—' if value is None else f'{value:,.{digits}f}'.replace(',', ' ').replace('.', ',')


def markets_html(context):
    context = context or {}
    groups = []
    for group in context.get('groups', []):
        rows=[]
        for row in group['rows']:
            change=row.get('change_pct')
            tone='gain' if change is not None and change>0 else 'loss' if change is not None and change<0 else 'muted'
            precision=4 if row['ticker'].startswith('FX_IDC:') else 2
            source=(f'<a href="{esc(row["source_url"])}" target="_blank" rel="noopener noreferrer">Source ↗</a>' if row.get('source_url') else '')
            rows.append(f'<article class="macro-quote" data-macro-ticker="{esc(row["ticker"])}"><div class="macro-price"><h3>{esc(row["name"])}</h3><strong>{number(row.get("value"),precision)}</strong></div>'
                f'<p><span>{esc(row["unit"])}</span> · <span class="{tone}">{number(change)} %</span></p>'
                f'<p class="fineprint">{esc(row.get("notice"))}<br><time>{esc(row.get("observed_at"))}</time><br>{esc(mode_label(row.get("mode")))} · {source}</p></article>')
        groups.append(f'<section class="macro-group"><h2>{esc(group["title"])}</h2>'+''.join(rows)+'</section>')
    errors=context.get('errors') or {}
    error_html=('<details><summary>Détails de collecte macro</summary><ul>'+''.join(f'<li>{esc(k)} : {esc(v)}</li>' for k,v in errors.items())+'</ul></details>') if errors else ''
    return (f'<div class="macro-status"><p>Collecte tentée : {esc(context.get("checked_at"))} · état {esc(context.get("status","non observé"))}. Horodatages en UTC.</p>{error_html}</div>'
        +'<div class="macro-grid">'+(''.join(groups) or '<p>Contexte international non encore collecté.</p>')+'</div>'
        +'<p class="fineprint">Source : TradingView, scanner public. Instantanés à chaque collecte Nour, pas de diffusion en direct. '
        'La variation est celle fournie par la source, pas un rendement depuis la collecte Nour. Les marchés ont des horaires différents : ces observations ne sont pas simultanées. '
        'Or, Brent, cuivre et charbon : contrats futures continus, pas prix spot. USD/MAD et EUR/MAD : cotations indicatives, pas cours officiel de Bank Al-Maghrib. '
        'Aucune imputation des cours absents ; aucune influence sur les scores ni prédiction du MASI.</p>')


def radar_html(articles):
    rows=[]
    for a in articles:
        tickers=', '.join(a.get('tickers') or [])
        scope=a.get('scope','MAROC' if a.get('classification')=='DOCUMENT_LISTED' else 'UNKNOWN')
        category=a.get('category','bvc' if tickers else 'autre')
        searchable=' '.join(str(a.get(k) or '') for k in ('title','publisher'))+' '+tickers
        rows.append(f'<article class="news-item" data-news-row data-search="{esc(searchable.lower())}" data-tier="{esc(a.get("tier"))}" data-scope="{esc(scope)}" data-category="{esc(category)}">'
            f'<span class="eyebrow">{esc(a.get("publisher"))} · {esc(a.get("published_at"))} · {esc(a.get("tier"))}</span>'
            f'<h2><a href="{esc(a.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(a.get("title"))} ↗</a></h2>'
            f'<p>{esc(SCOPES.get(scope,SCOPES["UNKNOWN"]))} · {esc(CATEGORIES.get(category,"Autres"))} · {esc(a.get("status"))}</p>'
            f'<p class="fineprint">Titres associés : {esc(tickers or "non établis")}. Métadonnées de veille, contenu non vérifié ; aucun score NLP.</p></article>')
    scopes=''.join(f'<option value="{esc(k)}">{esc(v)}</option>' for k,v in SCOPES.items())
    categories=''.join(f'<option value="{esc(k)}">{esc(v)}</option>' for k,v in CATEGORIES.items())
    return ('<section class="panel"><div class="filters news-filters"><input class="search" id="news-search" type="search" placeholder="Titre, société ou source" aria-label="Rechercher dans les actualités">'
        '<select id="news-scope" aria-label="Filtrer par périmètre"><option value="">Maroc et international</option>'+scopes+'</select>'
        '<select id="news-category" aria-label="Filtrer par thème"><option value="">Tous les thèmes</option>'+categories+'</select>'
        '<select id="news-tier" aria-label="Filtrer par niveau de source"><option value="">Toutes les sources</option><option value="S1">Publications institutionnelles / AMMC</option><option value="S2">Veille secondaire</option></select>'
        '<button type="button" id="news-reset">Réinitialiser</button></div>'
        f'<p id="news-count" role="status" aria-live="polite">{len(articles)} liens affichés</p>'
        '<p class="fineprint">S1 : présence sur l’index AMMC ou lien institutionnel direct HCP/Fed/BCE, sans validation de son contenu chiffré. '
        'S2 : alerte à recouper ; les relais Google News ne sont pas des sources primaires. Le thème provient du flux ; le périmètre géographique est distinct et peut rester non établi.</p>'
        '<div class="news-list">'+(''.join(rows) or '<p>Aucune publication disponible dans cette collecte.</p>')+'</div></section>')


def feed_health_html(health):
    rows=''.join(f'<li>{esc(s["name"])} : {esc(s["status"])} · {esc(s["items"])} métadonnées récentes</li>' for s in health.get('sources',[]))
    return (f'<details class="panel"><summary>État des flux · {esc(health.get("status","non observé"))}</summary>'
        f'<p>Dernière tentative : {esc(health.get("checked_at"))}. Un flux vide n’est pas un événement économique ; un échec ne renouvelle pas les dates des liens archivés.</p><ul>{rows}</ul>'
        +''.join(f'<p class="fineprint">{esc(error)}</p>' for error in health.get('errors',[]))+'</details>')
