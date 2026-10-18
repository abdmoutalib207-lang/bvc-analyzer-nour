"""Read-only universe queries, mirroring web/assistant-query.js.

Only select canonical scalar fields. Never impute, normalize or calculate ratios.
"""
from copy import deepcopy
import math
import re
from .assistant_context import normalize


def plan(question, catalog):
    q = normalize(question)
    found = [m for m in catalog if re.search(r'\b(?:'+m['pattern']+')', q)]
    if any(m['id']=='macd' for m in found):
        chosen='histogram' if 'histogramme' in q else 'signal' if 'signal' in q else 'macd'
        found=[m for m in found if m['id'] not in ('macd','signal','histogram') or m['id']==chosen]
    if not re.search(r'quell?e?s?(?: sont)?(?: les)? (?:valeurs|titres|societes|entreprises|actions)|(?:affiche|montre|cherche|recherche|trouve|donne).*(?:valeurs|titres|societes|entreprises|actions)|liste|classement|classer|filtr|palmares|top\s*\d*|les\s+\d+|(?:valeurs|titres|societes|entreprises|actions) (?:avec|ayant|dont|qui ont)|toute la cote', q) or not found:
        return None
    years = list(dict.fromkeys(re.findall(r'\b20\d{2}\b', q)))
    missing = bool(re.search(r'indisponibl|manquant|suspend|absent|non (?:calcula|rapproch)', q))
    blocked=bool(re.search(r'suspend|bloqu',q))
    p = dict(metrics=[m['id'] for m in found], filters=[], missing=missing or blocked, blocked=blocked,
             year=int(years[0]) if years else None, sort=None, limit=5, error=None)
    indicator=re.search(r'\brsi\s*(\d+)\b',q)
    if indicator and int(indicator[1])!=14:
        p['error']='Seul le RSI 14 est disponible dans ce relevé ; aucun autre RSI n’est déduit.'
    if re.search(r'\bou\b|\bs[12]\b|semestr|ttm|prevision|normalise', q) or len(years)>1:
        p['error'] = 'Ce filtre exige une période ou une logique non prise en charge. Utilisez des critères annuels reliés par « et », avec un seul exercice.'
    requested = re.search(r'(?:top\s*|les\s+)(\d+)\b', q)
    if requested:
        p['limit'] = max(1, min(20, int(requested[1])))
    for m in found:
        match = re.search(r'\b(?:'+m['pattern']+r')\s*(?:(?:est|soit|annuel|annuelle)\s*)?(inferieur(?:e)?(?:s)? a|superieur(?:e)?(?:s)? a|au moins|au plus|moins de|plus de|<=|>=|<|>|=)\s*(-?\d+(?:[.,]\d+)?)', q)
        if match:
            op, number = match.groups()
            op = '<' if re.search(r'inferieur|moins de|^<$',op) else '>' if re.search(r'superieur|plus de|^>$',op) else '>=' if re.search(r'au moins|>=',op) else '<=' if re.search(r'au plus|<=',op) else '='
            p['filters'].append(dict(id=m['id'],op=op,value=float(number.replace(',','.'))))
            unit=re.match(r'\s*(%|mmad\b|mdh\b|mad\b|milliards?\b|millions?\b|points?\b|x\b)',q[match.end():])
            if unit and ('mmad' if unit[1]=='mdh' else unit[1])!=normalize(m['unit']):
                p['error']='Unité du seuil incompatible : '+m['label']+' utilise '+(m['unit'] or 'une valeur sans unité')+'. Aucun changement d’unité automatique.'
            if re.match(r'\s*(?:[\d.,]|e[+-]?\d)',q[match.end():]):
                p['error']='Nombre ambigu : utilisez un nombre sans séparateur de milliers, avec une virgule ou un point décimal.'
    if re.search(r'plus (?:faibles?|bas|petits?)|\bcroissant\b',q):
        p['sort'] = dict(id=found[0]['id'],direction='asc')
    elif re.search(r'plus (?:eleves?|hauts?|grands?|forts?)|\bdecroissant\b',q):
        p['sort'] = dict(id=found[0]['id'],direction='desc')
    if 'meilleur' in q:
        p['error']='Un ratio ne définit pas les meilleurs titres. Précisez un seuil ou un ordre croissant ou décroissant.'
    if re.search(r'entre\s+-?\d|compris|au.dessus|au.dessous|sous (?:la |les )?(?:mm|ema|sma)|surachet|survend',q):
        p['error']='Ce critère relatif ou cet intervalle n’est pas pris en charge. Précisez un seuil numérique explicite sur une mesure.'
    if re.search(r'classement|palmares|top\b|les\s+\d+',q) and not p['sort'] and not missing:
        p['error'] = 'Précisez le classement : par exemple « les 5 PER les plus faibles en 2025 ».'
    operators=re.findall(r'[<>]=?|inferieur(?:e)?s? a|superieur(?:e)?s? a|au moins|au plus|moins de|plus de|=',q)
    if len(operators)!=len(p['filters']):
        p['error'] = 'Critère numérique non reconnu : utilisez par exemple « PER inférieur à 15 et ROE supérieur à 10 % ».'
    return p


def get(row, path):
    for k in path.split('.'):
        row = row.get(k) if isinstance(row,dict) else None
    return row


def numeric(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def select(data,question):
    catalog = data.get('metric_catalog') or data.get('knowledge',{}).get('metric_catalog',[])
    p = plan(question,catalog)
    if p is None:
        return None
    result = dict(p,rows=[],matched=0,excluded_missing=0,excluded_period=0,universe=len(data.get('symbols',{})))
    if p['error']:
        return result
    definitions = [m for m in catalog if m['id'] in p['metrics']]
    financial = any(m['domain']=='fundamentals' for m in definitions)
    if p['year'] and not financial:
        result['error']='Les classements techniques ou de risque à un exercice historique ne sont pas reconstruits. Retirez l’année pour consulter le dernier relevé daté.'
        return result
    q=normalize(question)
    sectors=[s for s in sorted({r.get('sector') for r in data.get('symbols',{}).values() if r.get('sector')}) if re.search(r'\b'+normalize(s)+r's?\b',q)]
    if re.search(r'secteur|banques?|assuran|immobilier|industr|mines|technolog|telecom|agroaliment|construct|materiaux|transport|energie|finance|holding|tourisme|distribution|automobile|sante',q) and len(sectors)!=1:
        result['error']='Précisez un seul secteur du référentiel Nour, par exemple « secteur Banque » ou « secteur Immobilier ».'
        return result
    result['sector']=sectors[0] if sectors else None
    proof_keys={'pe':['resultat_net_part_groupe','resultat_net','nombre_actions'],'eps':['resultat_net_part_groupe','resultat_net','nombre_actions'],
                'pb':['capitaux_propres_part_groupe','capitaux_propres','nombre_actions'], 'roe':['resultat_net_part_groupe','resultat_net','capitaux_propres_part_groupe','capitaux_propres']}
    def compare(value,f):
        return {'<':lambda:value<f['value'], '>':lambda:value>f['value'],
                '<=':lambda:value<=f['value'], '>=':lambda:value>=f['value'],
                '=':lambda:value==f['value']}[f['op']]()
    for symbol,row in sorted(data.get('symbols',{}).items()):
        if result['sector'] and row.get('sector')!=result['sector']:
            continue
        f = row.get('fundamental') or {}
        if p['year'] and financial and f.get('exercise')!=p['year']:
            result['excluded_period']+=1
            continue
        values = {m['id']:get(row,m['path']) if numeric(get(row,m['path'])) else None for m in definitions}
        absent = any(v is None for v in values.values())
        if p['blocked'] and not any((f.get('metric_availability') or {}).get(m['path'].split('.')[-1],{}).get('status')=='blocked' for m in definitions):
            continue
        if (not absent) if p['missing'] else absent:
            if not p['missing']:
                result['excluded_missing']+=1
            continue
        if not all(numeric(values[c['id']]) and compare(values[c['id']],c) for c in p['filters']):
            continue
        picked = {k:deepcopy(row.get(k)) for k in ('name','sector','url','asof','price_source','history_readiness')}
        picked.update({k:deepcopy(f.get(k)) for k in ('exercise','period_end','currency','accounting_basis','validation_status','document_url')})
        picked.update(symbol=symbol,values=values,warnings=deepcopy(f.get('warnings') or []) if financial else [],latest_report=deepcopy(f.get('latest_report') or None) if financial else None,
                      evidence={k:deepcopy(v) for k,v in (f.get('evidence') or {}).items() if any(k in proof_keys.get(m['id'],[]) for m in definitions)},metric_availability=deepcopy(f.get('metric_availability') or {}) if financial else {},
                      collection_conflicts=deepcopy(row.get('collection_conflicts') or []),
                      risk_window=deepcopy(row.get('market_risk')) if any(m['domain']=='risk' for m in definitions) else None)
        result['rows'].append(picked)
    if p['sort']:
        order = 1 if p['sort']['direction']=='asc' else -1
        result['rows'].sort(key=lambda r:(order*r['values'][p['sort']['id']],r['symbol']))
    result['matched']=len(result['rows'])
    result['rows']=result['rows'][:p['limit']]
    result['notice']='Sélection descriptive des chiffres publiés par Nour, avec réserves ; aucune recommandation. Les périmètres, devises et dates peuvent différer : ce classement ne constitue pas une comparaison sectorielle validée. Les valeurs absentes ne valent jamais zéro.'
    return result
