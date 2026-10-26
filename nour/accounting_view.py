"""Quiet, discoverable accounting reference generated from the published report."""
from collections import defaultdict
from html import escape

from .accounting import coverage, knowledge


def body(report):
    esc = lambda value: escape(str(value or 'À préciser'), quote=True)
    count = coverage(report['results'])
    topics = ''.join('<details class="reading-details"><summary>'+esc(t['title'])+'</summary>'
        '<p>'+esc(t['text'])+'</p><ul>'+''.join(
            '<li><a href="'+esc(s['url'])+'" target="_blank" rel="noopener noreferrer">'+esc(s['title'])+'</a></li>'
            for s in t['sources'])+'</ul></details>' for t in knowledge()['topics'].values())
    rows, families = [], defaultdict(list)
    states = {'primary_scoped_review':'Méthodes contrôlées sur pages sélectionnées',
              'declared_to_review':'Référentiel relevé ; méthodes à compléter',
              'missing':'Publication à compléter', 'document_conflict':'Périmètre à rapprocher',
              'unavailable':'Revue à compléter'}
    for row in sorted(report['results'], key=lambda r:r['symbol']):
        p = row.get('accounting_profile') or {}
        families[p.get('family') or row.get('sector')].append(row['symbol'])
        source = p.get('evidence') or []
        url = source[0]['url'] if source else p.get('document_url')
        link = '<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Publication ↗</a>' if url else 'À rechercher'
        rows.append('<tr><td><a href="titres/'+esc(row['symbol'])+'.html#verifications">'+esc(row['symbol'])+'</a></td>'
            '<td>'+esc(p.get('family'))+'</td><td>'+esc(p.get('declared_basis'))+'</td>'
            '<td>'+esc(p.get('period_end'))+'</td><td>'+esc(states.get(p.get('status'),p.get('status')))+'</td><td>'+link+'</td></tr>')
    family_list = ''.join('<li>'+esc(family)+' : '+esc(', '.join(symbols))+'</li>'
                          for family,symbols in sorted(families.items(),key=lambda v:str(v[0])))
    return ('<main><a href="metiers.html">← Métiers</a><div class="hero"><div><span class="eyebrow">Comprendre les publications</span>'
        '<h1>Méthodes comptables</h1><p>Le référentiel dépend de la société, du document et de la période.</p>'
        '<button type="button" data-assistant-question="Quelles normes comptables selon chaque secteur marocain ?">Demander à Nour</button></div></div>'
        '<section class="panel"><h2>Les notions utiles</h2>'+topics+'</section>'
        '<section class="panel"><h2>Référentiels des 80 titres</h2><p>'
        +str(count['primary_scoped_reviews'])+' sociétés avec pages de méthodes contrôlées dans ce lot ; '
        +str(count['declared_to_review'])+' déclarations restant à approfondir. Les chiffres publiés restent consultables.</p>'
        '<div class="tablewrap"><table><thead><tr><th>Titre</th><th>Métier</th><th>Référentiel du document</th><th>Clôture comptable</th><th>Lecture des méthodes</th><th>Source</th></tr></thead>'
        '<tbody>'+''.join(rows)+'</tbody></table></div></section>'
        '<details class="reading-details"><summary>Familles suivies</summary><ul>'+family_list+'</ul></details>'
        '<p class="fineprint">Les règles générales expliquent les comptes ; elles ne convertissent aucun résultat, ne certifient pas tous les rapports et ne modifient pas le score.</p></main>')
