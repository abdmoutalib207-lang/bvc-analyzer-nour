"""Read-only screener of canonical annual ratios, never external imputations."""
import csv
import html
import json
import math
import unicodedata


def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rows(report):
    output = []
    for item in report['results']:
        f = item.get('fundamental') or {}
        output.append({
            'symbol': item['symbol'], 'name': item['name'], 'sector': item.get('sector') or 'Autre',
            'annual_exercise': f.get('exercise'), 'annual_period_end': f.get('period_end'),
            'accounting_basis': f.get('accounting_basis'), 'currency': f.get('currency'),
            'price_date': item.get('asof'), 'price_mad': item.get('price'),
            **{key: f.get(key) if numeric(f.get(key)) else None for key in ('eps_mad','pe','pb','roe_pct')},
            'validation_status': f.get('validation_status'), 'document_url': f.get('document_url'),
            'warnings': list(f.get('warnings') or []),
        })
    return output


def panel(report):
    data = rows(report)
    sectors = ''.join(f'<option>{esc(s)}</option>' for s in sorted({r['sector'] for r in data}))
    body = []
    for row in data:
        payload = {k: row[k] for k in ('sector','eps_mad','pe','pb','roe_pct','annual_exercise')}
        term = ''.join(c for c in unicodedata.normalize('NFD',row['symbol']+' '+row['name']) if unicodedata.category(c)!='Mn').lower()
        def amount(key):
            return f"{row[key]:,.2f}".replace(',', ' ').replace('.', ',') if numeric(row[key]) else 'Indisponible'
        body.append(f'<tr data-fundamental-row data-search="{esc(term)}" data-facts="{esc(json.dumps(payload))}">'
            f'<td><a href="titres/{esc(row["symbol"])}.html">{esc(row["symbol"])}</a></td>'
            f'<td>{esc(row["annual_exercise"]) or "Absent"}<small> · {esc(row["annual_period_end"])}</small></td>'
            f'<td>{esc(row["accounting_basis"]) or "Non renseigné"} · {esc(row["currency"])}</td>'
            + ''.join(f'<td>{amount(k)}</td>' for k in ('eps_mad','pe','pb','roe_pct'))
            + f'<td>{esc(row["price_date"]) or "Indisponible"}</td>'
            + f'<td><a href="titres/{esc(row["symbol"])}.html">Sources et réserves</a></td></tr>')
    return ('<details class="panel" id="fundamental-explorer"><summary>Explorer les fondamentaux des 80 titres</summary>'
        '<p>Les mêmes calculs annuels que les fiches Nour, avec leurs périodes et leurs cours datés. '
        'BPA en MAD ; PER et P/B en multiples ; ROE de clôture en %. Aucun ratio manquant n’est remplacé par zéro.</p>'
        '<div class="filters"><input class="search" type="search" id="fundamental-search" aria-label="Rechercher dans les fondamentaux" placeholder="Code ou société">'
        f'<select id="fundamental-sector" aria-label="Secteur des fondamentaux"><option value="">Tous les secteurs</option>{sectors}</select>'
        '<select id="fundamental-availability" aria-label="Disponibilité des fondamentaux">'
        '<option value="">Toutes les couvertures</option><option value="eps_mad">BPA disponible</option>'
        '<option value="pe">PER disponible</option><option value="pb">P/B disponible</option>'
        '<option value="roe_pct">ROE disponible</option><option value="missing_eps">BPA à compléter</option>'
        '<option value="missing_annual">Exercice annuel absent</option></select>'
        '<label>PER maximum <input id="fundamental-pe-max" type="number" min="0" step="any" inputmode="decimal"></label>'
        '<label>ROE minimum (%) <input id="fundamental-roe-min" type="number" step="any" inputmode="decimal"></label>'
        '<button type="button" id="fundamental-reset">Effacer les filtres</button></div>'
        f'<p id="fundamental-count" role="status">{len(data)} titres affichés</p>'
        '<div class="tablewrap"><table><thead><tr><th>Code</th><th>Annuel</th><th>Périmètre et devise</th>'
        '<th>BPA</th><th>PER</th><th>P/B</th><th>ROE %</th><th>Date du cours</th><th>Vérification</th></tr></thead>'
        '<tbody>'+''.join(body)+'</tbody></table></div>'
        '<p><a class="btnlink outline" href="fondamentaux.csv" download>Exporter les fondamentaux CSV</a></p>'
        '<p class="fineprint">Un filtre est une sélection de données, pas une recommandation ni une médiane sectorielle. '
        'Vérifiez les exercices, normes, périmètres, dates et réserves avant toute comparaison. '
        'Les semestres restent séparés dans les fiches ; aucun TTM n’est reconstitué.</p></details>')


def export_csv(report, path):
    data = rows(report)
    fields = ('symbol','name','sector','annual_exercise','annual_period_end','accounting_basis','currency',
              'price_date','price_mad','eps_mad','pe','pb','roe_pct','validation_status','document_url','warnings')
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
        writer.writeheader()
        for row in data:
            writer.writerow({**row, 'warnings': ' | '.join(row['warnings'])})
