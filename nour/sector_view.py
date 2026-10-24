"""Readable formula/input coverage; missing business data stays missing."""
from html import escape
from collections import Counter
from urllib.parse import urlsplit
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
        sources=''
        for field, fact in m.get('inputs',{}).items():
            url = fact.get('url')
            link = (f'<a href="{e(url)}" rel="noopener noreferrer">Document primaire</a>'
                    if isinstance(url,str) and urlsplit(url).scheme == 'https' else 'Source non vérifiée')
            original = (f' · publié {e(fact["valeur_au_rapport"])} {e(fact.get("unite_au_rapport"))}'
                        if fact.get('valeur_au_rapport') is not None else '')
            pieces = ''.join(f'<li>{e(c.get("label"))} : {e(c.get("valeur_au_rapport"))} {e(c.get("unite_au_rapport"))}</li>'
                             for c in fact.get('components',[]) if isinstance(c,dict))
            sources += (f'<li>{e(field)} · {e(fact.get("valeur"))} {e(fact.get("unite"))}{original}'
                        f' · page {e(fact.get("page"))} · {e(fact.get("period_end"))} · {link}'
                        +(f'<ul>{pieces}</ul>' if pieces else '')+f'<p>{e(fact.get("note",""))}</p></li>')
        rows.append(f'<tr data-sector-metric="{e(key)}"><td>{e(m["label"])}</td><td>{value}</td>'
            f'<td><details><summary>Formule, pièces et limites</summary><p>{e(m["formula"])}</p>'
            f'<p>{e(m["formula_version"])} · {e(m.get("period_end"))} · {e(m.get("accounting_basis"))}</p>'
            +(f'<p>Entrées en {e(m.get("currency"))} ; ratio sans conversion de change. Aucun montant en MAD déduit.</p>'
              if m.get('currency_method') == 'same_currency_ratio_no_fx' and m.get('currency') != 'MAD' else '')+
            f'<ul>{sources}</ul><p>{e(reason)} {e(m.get("notes"))}</p>'
            f'<a href="{e(m["methodology_url"])}" rel="noopener noreferrer">Référence méthodologique</a>'
            '</details></td></tr>')
    kpis=''.join('<li>'+e(k['label'])+((' · '+e(k['source'].get('period_end'))) if k.get('value') is not None and isinstance(k.get('source'),dict) else '')+' : '+(e(k['value'])+' '+e(k['unit']) if k['value'] is not None else e(k['reason']) if k.get('status')=='published_breakdown' else 'Indisponible — '+e(k['reason']))+'</li>' for k in sector.get('published_kpis',{}).values())
    return ('<section class="panel" data-sector-calculators><h2>Calculs du métier</h2>'
        f'<p>{e(sector.get("family"))} · Méthodes séparées du score. Les chiffres publiés sont présentés séparément des ratios calculables.</p>'
        +('<h3>Indicateurs publiés du métier</h3><ul>'+kpis+'</ul>' if kpis else '')+reported_facts_card(sector.get('reported_facts') or {})+business_disclosures_card(sector.get('business_disclosures') or {})+'<div class="tablewrap"><table><thead><tr><th>Indicateur</th><th>Valeur</th><th>Traçabilité</th></tr></thead><tbody>'
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


def business_disclosures_card(block):
    """Display raw published figures even when no compatible ratio exists."""
    from decimal import Decimal
    e = lambda x: escape(str(x if x is not None else 'Non communiqué'))
    records = block.get('records', [])
    if not records:
        return ''
    labels = {'production': 'Production par métal et filiale', 'expenses': 'Charges comptables publiées',
              'investments': 'Investissements de gestion', 'cash_flows': 'Décaissements et flux de trésorerie', 'activity':'Indicateurs opérationnels publiés', 'backlog':'Carnet de commandes publié', 'unit_cost':'Coûts unitaires publiés'}
    groups = {}
    for row in records:
        groups.setdefault((row.get('category'), row.get('period_end'), row.get('period_kind')), []).append(row)
    parts = []
    for category in labels:
        for (cat, end, kind), rows in sorted(groups.items(), key=lambda x: str(x[0][1]), reverse=True):
            if cat != category:
                continue
            period = ('S1 ' if kind == 'semester' else 'Année ') + str(end)[:4]
            body = []
            for row in rows:
                value = 'Indisponible'
                if row['value'] is not None:
                    number = format(Decimal(str(row['value'])), ',f')
                    if '.' in number:
                        number = number.rstrip('0').rstrip('.')
                    value = ('≈ ' if row.get('approximate') else '') + e(number.replace(',', ' ').replace('.', ',')) + ' ' + e(row['unit'])
                source = row.get('source') or {}
                url = source.get('url', '')
                link = (f'<a href="{e(url)}#page={e(row.get("page"))}" rel="noopener noreferrer">{e(source.get("title"))} · page PDF {e(row.get("page"))}</a>'
                        if row.get('status') in ('primary_page_checked','automatic_text_extracted') else 'Preuve non vérifiée')
                body.append(f'<tr data-business-id="{e(row.get("id"))}" data-business-value="{e(row.get("value"))}">'
                    f'<td>{e(row.get("label"))}<small class="quote-kind">{e(row.get("scope"))}</small></td>'
                    f'<td>{value}</td><td><details><summary>Source et définition</summary>{link}'
                    f'<p>{"Lecture automatique, à confirmer si le document change." if row.get("status")=="automatic_text_extracted" else "Page contrôlée pour cette version du document."}</p><p>Page imprimée {e(row.get("printed_page"))} · {e(row.get("period_start"))} → {e(end)}</p>'
                    f'<p>{e(row.get("definition"))}</p><p>{e(row.get("note", ""))}</p>'
                    +(f'<p>{e(row["reason"])}</p>' if row.get('reason') else '')
                    +f'<small class="source-hash">{e(source.get("document_hash"))}</small></details></td></tr>')
            opened = ' open' if category in ('production', 'cash_flows') and end == max(str(r.get('period_end')) for r in records if r.get('category') == category) else ''
            parts.append(f'<details data-business-group="{e(category)}-{e(end)}"{opened}><summary>{e(labels[category])} · {e(period)} · {len(rows)} chiffres</summary>'
                '<div class="tablewrap"><table><thead><tr><th>Indicateur et périmètre</th><th>Valeur publiée</th><th>Traçabilité</th></tr></thead><tbody>'
                + ''.join(body) + '</tbody></table></div></details>')
    meanings={'TC':'tonnes de concentré','kg':'kilogrammes','TM':'tonnes métriques','MDH':'millions de dirhams',
              'EVP':'équivalent vingt pieds','USD/oz':'dollars par once','t':'tonnes',
              'g Ag/t':'grammes d’argent par tonne','%':'pourcentage','millions de tonnes':'millions de tonnes'}
    units=list(dict.fromkeys(r.get('unit') for r in records if r.get('unit')))
    intro='Unités publiées : '+' ; '.join(str(u)+' = '+meanings.get(u,str(u)) for u in units)+'.'
    if any(r.get('approximate') for r in records):intro+=' ≈ indique une valeur approximative publiée.'
    if any(r.get('category')=='cash_flows' for r in records):intro+=' Les flux conservent le signe du tableau de trésorerie.'
    return ('<div id="chiffres-metier" class="business-disclosures" data-business-disclosures><h3>Chiffres officiels du métier</h3>'
        '<p>'+e(intro)+'</p>'
        + ('<p>Dernière collecte partielle : les chiffres datés déjà disponibles sont conservés.</p>' if block.get('collection_status')=='partial' else '<p>Des éléments de la dernière collecte restent à vérifier.</p>' if block.get('collection_status')=='needs_review' else '') + ''.join(parts) + '<details data-business-reservations><summary>Réserves et points restant à vérifier</summary><ul>'
        + ''.join('<li>' + e(note) + '</li>' for note in block.get('reservations', [])) + '</ul></details>'
        + f'<p>Relevé daté du {e(block.get("reviewed_on"))} · disponible dans Nour depuis le {e(block.get("available_from"))} · hors score.</p></div>')


def reported_facts_card(block):
    from decimal import Decimal
    e=lambda x:escape(str(x if x is not None else 'À préciser'))
    rows=block.get('records') or []
    if not rows:
        return '<p data-reported-empty>Les relevés chiffrés restent à compléter dans Nour. Les documents référencés peuvent contenir d’autres informations.</p>'
    items=[]
    for r in rows:
        n=format(Decimal(str(r['value'])),',f')
        if '.' in n:n=n.rstrip('0').rstrip('.')
        value=n.replace(',',' ').replace('.',',')
        source=r['source'];url=source['url'];page=source.get('page')
        if isinstance(page,int) and not isinstance(page,bool) and page>0:url+='#page='+str(page)
        status='Page contrôlée dans le relevé existant' if r['status']=='page_checked' else 'Lecture à confirmer'
        period=r.get('period_end') or ('Dossier '+str(r.get('period_context') or 'non daté')+' ; période propre à préciser')
        items.append(f'<tr data-reported-id="{e(r["id"])}"><td>{e(r["label"])}<small class="quote-kind">{e(r["scope"])}</small></td>'
            f'<td>{e(value)} {e(r["unit"])}<small class="quote-kind">{e(period)}</small></td>'
            f'<td><details><summary>{e(status)} · source et réserves</summary>'
            f'<a href="{e(url)}" rel="noopener noreferrer">Document référencé</a>'
            + (f'<p>Page PDF {e(page)}</p>' if page is not None else f'<p>{e(source.get("page_hint") or "Page exacte à préciser")}</p>')
            + f'<p>{e(r.get("notice") or "Le contrôle de cette pièce ne certifie pas tout le rapport.")}</p><p>{e(r.get("note") or "")}</p></details></td></tr>')
    return ('<details id="releves-disponibles" data-reported-facts class="business-disclosures"><summary>'
        f'Chiffres documentés disponibles · {len(rows)} relevés</summary><p>{e(block.get("notice"))}</p>'
        '<div class="tablewrap"><table><thead><tr><th>Indicateur et périmètre</th><th>Valeur et période</th><th>Source et niveau de lecture</th></tr></thead><tbody>'
        +''.join(items)+'</tbody></table></div><ul>'+''.join('<li>'+e(x)+'</li>' for x in block.get('reservations',[]))+'</ul></details>')
