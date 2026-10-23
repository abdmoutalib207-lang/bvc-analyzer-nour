"""Readable formula/input coverage; missing business data stays missing."""
from html import escape
from collections import Counter
from .financial_audit import METRICS


def coverage_report(report):
    records=[]
    for row in report['results']:
        f=row['fundamental'];sector=row.get('sector_indicators') or {}
        blocked=set(f.get('financial_audit',{}).get('blocked_metrics',[]))
        records.append(dict(symbol=row['symbol'],name=row.get('name'),family=sector.get('family'),
            identity=row.get('issuer_identity'),annual_exercise=f.get('exercise'),
            period_end=f.get('period_end'),currency=f.get('currency'),accounting_basis=f.get('accounting_basis'),
            formula_version=f.get('calculation_version'),fact_evidence=f.get('evidence'),
            verification_status=f.get('financial_audit',{}).get('status'),
            annual_document=f.get('document_url'),semester=f.get('latest_report'),
            fundamental={k:dict(value=f.get(k),status='blocked' if k in blocked else 'available' if f.get(k) is not None else 'missing',
                reasons=f.get('metric_availability',{}).get(k,{}).get('reason_codes',[])) for k in METRICS},
            sector=sector,reservations=f.get('warnings',[]),source_certified=False))
    return dict(version='nour-coverage-v1',analysis_date=report['analysis_date'],universe=len(records),
                issuers=records,documents_certified=False)


def sector_card(row):
    sector=row.get('sector_indicators') or {};rows=[]
    e=lambda x:escape(str(x if x is not None else 'Non communiqué'))
    for key,m in sector.get('metrics',{}).items():
        value=e(m['value'])+' '+e(m['unit']) if m['value'] is not None else 'Indisponible'
        reason=' ; '.join(x['reason'] for x in m['reasons'])
        sources=''.join(f'<li>{e(k)} · {e(v.get("valeur"))} {e(v.get("unite"))} · page {e(v.get("page"))} · {e(v.get("period_end"))}</li>'
                        for k,v in m.get('inputs',{}).items())
        rows.append(f'<tr data-sector-metric="{e(key)}"><td>{e(m["label"])}</td><td>{value}</td>'
            f'<td><details><summary>Formule, pièces et limites</summary><p>{e(m["formula"])}</p>'
            f'<p>{e(m["formula_version"])} · {e(m.get("period_end"))} · {e(m.get("accounting_basis"))}</p>'
            f'<ul>{sources}</ul><p>{e(reason)} {e(m.get("notes"))}</p>'
            f'<a href="{e(m["methodology_url"])}" rel="noopener noreferrer">Référence méthodologique</a>'
            '</details></td></tr>')
    kpis=''.join('<li>'+e(k['label'])+' : '+(e(k['value'])+' '+e(k['unit']) if k['value'] is not None else 'Indisponible — '+e(k['reason']))+'</li>' for k in sector.get('published_kpis',{}).values())
    return ('<section class="panel" data-sector-calculators><h2>Calculs du métier</h2>'
        f'<p>{e(sector.get("family"))} · Méthodes séparées du score. Une formule implémentée ne signifie pas que ses données sont publiées.</p>'
        +('<h3>Indicateurs publiés du métier</h3><ul>'+kpis+'</ul>' if kpis else '')+'<div class="tablewrap"><table><thead><tr><th>Indicateur</th><th>Valeur</th><th>Traçabilité</th></tr></thead><tbody>'
        +''.join(rows)+'</tbody></table></div><p><a href="../couverture.json">Entrées et état de couverture des 80 sociétés</a></p></section>')


def quality_card(row):
    e=lambda x:escape(str(x if x is not None else 'Non communiqué'))
    issues=row.get('resilience',{}).get('anomalies',[])
    old=row.get('last_healthy')
    return ('<section class="panel" data-issuer-diagnostics><h2>Qualité et fraîcheur</h2>'
        f'<p>État : {e(row["decision"])} · Source utilisée : {e(row.get("price_source"))}.</p>'
        f'<p>Dernier traitement validé du titre : {e(row.get("last_validated_at"))}. La date de cotation ci-dessus conserve sa valeur réelle.</p>'
        '<p>Une cotation inchangée ne prouve pas une panne. Les heures inconnues restent non communiquées.</p>'
        +''.join(f'<p class="banner">{e(x["reason"])}</p>' for x in issues)
        +(f'<p>Dernier état sain conservé : séance {e(old.get("asof"))}, contrôlé {e(old.get("validated_at"))}. '
          'Archive distincte ; aucune nouvelle cotation attestée.</p>' if old else '')
        +f'<a href="../anomalies.html">Historique des anomalies de {e(row["symbol"])}</a></section>')
