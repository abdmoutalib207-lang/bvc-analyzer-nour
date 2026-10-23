"""Persistent local anomalies; disappearance/source failure is not resolution."""
from copy import deepcopy
from hashlib import sha256
from html import escape
import json
import re


def observations(report):
    out=[]
    for row in report['results']:
        s=row['symbol']
        for entry in row.get('resilience',{}).get('anomalies',[]):
            out.append(deepcopy(entry))
        for check in row.get('fundamental',{}).get('financial_audit',{}).get('checks',[]):
            if check['status'] not in ('blocked','review_required'):continue
            out.append(dict(symbol=s,domain='financial',code=check['code'],
                reason=check.get('detail') or check['code'].replace('_',' '),
                severity='blocking_local' if check['status']=='blocked' else 'warning',
                source=row['fundamental'].get('document_url'),
                metrics=['fundamental.'+m for m in check.get('blocked_metrics',[])],fields=check.get('fields',[]),
                action='Rapprocher les pages et définitions concernées ; ne pas inventer de chiffre.'))
        for text in row.get('quality',{}).get('issues',[]):
            out.append(dict(symbol=s,domain='history' if 'historique' in text.lower() else 'price',
                code='data_quality_'+sha256(re.sub(r'\d+', '#', text).encode()).hexdigest()[:12],reason=text,
                severity='info' if row['decision']=='SUSPENDU' else 'warning',
                source=row.get('price_source'),metrics=['price'],
                action='Vérifier la séance réelle et la source ; conserver la date propre de la cotation.'))
    health=report.get('health') or {}
    if health.get('result') in ('error','awaiting_quotes'):
        out.append(dict(symbol='GLOBAL',domain='source',code='collection_no_usable_update',reason=health.get('message') or 'Aucune donnée nouvelle exploitable',
            severity='warning',source=health.get('source'),metrics=['freshness'],action='Source à contrôler ; dates des données conservées inchangées.'))
    for entry in report.get('collection',{}).get('conflicts',[]):
        if entry.get('symbol'):
            out.append(dict(symbol=entry['symbol'],domain='source',code='collection_conflict',
                reason=entry.get('reason') or 'Observation contradictoire conservée',severity='blocking_local',
                source=entry.get('source'),metrics=['price'],evidence=deepcopy(entry),
                action='Rapprochement des observations conservées requis.'))
    return out


def update_journal(previous, report, now):
    out=deepcopy(previous or {'schema_version':1,'entries':{}})
    rows={r['symbol']:r for r in report['results']}
    active=set()
    for entry in observations(report):
        identity={k:entry.get(k) for k in ('symbol','domain','code','metrics','source')}
        key=sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        active.add(key);old=out['entries'].get(key)
        if old:
            old.update(last_seen=now,occurrences=old['occurrences']+(old['last_seen']!=now),
                       state=('persistent' if old['state']!='resolved' else 'new') if old['last_seen']!=now else old['state'])
            if old['state']=='new':old['reopened']=old.get('reopened',0)+1
            latest=old.get('latest_observation') or {k:old.get(k) for k in entry}
            if latest!=entry:
                old.setdefault('observation_history',[]).append({'at':now,'observation':deepcopy(entry)})
            old['latest_observation']=deepcopy(entry)
        else:
            out['entries'][key]={**entry,'id':key,'name':rows.get(entry['symbol'],{}).get('name'),
                'first_seen':now,'last_seen':now,'state':'new','occurrences':1,'resolutions':[]}
    for key,entry in out['entries'].items():
        if key in active or entry['state']=='resolved':continue
        row=rows.get(entry['symbol']);valid=False
        if entry['symbol']=='GLOBAL' and entry['domain']=='source':
            health=report.get('health') or {}
            valid=bool(health.get('result') in ('updated','partial','intraday','unchanged','reconciled')
                and ((health.get('details') or {}).get('observations_refreshed') or (report.get('intraday') or {}).get('quotes')))
        if row and not row.get('resilience',{}).get('anomalies'):
            if entry['domain'] in ('price','source'):
                valid=bool(row.get('price') and row.get('source_checked_at') and row.get('price_validated_at')
                    and row['source_checked_at']==row['price_validated_at'] and row['decision']!='INDISPONIBLE')
            elif entry['domain']=='financial' and entry.get('metrics'):
                valid=all(row['fundamental'].get(m.split('.')[-1]) is not None
                          and m.split('.')[-1] not in row['fundamental']['financial_audit']['blocked_metrics']
                          for m in entry['metrics'])
            elif entry['domain']=='financial' and entry.get('fields'):
                evidence=row['fundamental'].get('evidence') or {}
                from .financial_audit import REVIEWED
                valid=all((evidence.get(k) or {}).get('validation_status') in REVIEWED
                    and (evidence.get(k) or {}).get('document_hash') for k in entry['fields'])
            elif entry['domain']=='history':
                valid=bool(row.get('quality',{}).get('usable_close_bars',0)>=50
                    and row.get('price_validated_at') and row.get('source_checked_at')==row['price_validated_at'])
            elif entry['domain']=='technical':
                valid=all((all(row.get('technical',{}).get(k) is not None for k in ('sma20','sma50','rsi14')) if m=='technical' else row.get('technical',{}).get(m.split('.')[-1]) is not None) for m in entry.get('metrics',[]))
            elif entry['domain']=='presentation':
                valid=row.get('page_render_status')=='available'
        if valid:
            entry['state']='resolved';entry['resolved_at']=now
            entry['resolutions'].append({'at':now,'proof':'Nouvelle validation positive des données/indicateurs concernés',
                'generator_commit':report.get('runtime',{}).get('commit')})
    out['checked_at']=now
    out['active_count']=sum(x['state']!='resolved' for x in out['entries'].values())
    return out


LABELS={'financial':'Financier','price':'Prix','volume':'Volume','history':'Historique','technical':'Technique',
    'source':'Source','publication':'Publication','info':'Information','warning':'Avertissement',
    'blocking_local':'Bloquant local','critical_global':'Critique global','new':'Nouveau','persistent':'Persistant','resolved':'Résolu'}


def dashboard(journal, report):
    esc=lambda x:escape(str(x if x is not None else 'Non communiqué'))
    rows=[]
    for entry in sorted(journal['entries'].values(),key=lambda x:(x['state']=='resolved',x['symbol'],x['first_seen'])):
        attrs=' '.join(f'data-{k}="{esc(entry.get(k))}"' for k in ('symbol','domain','severity','source'))
        rows.append(f'<tr data-anomaly-row {attrs}><td>{esc(entry["symbol"])}<br>{esc(entry.get("name"))}</td>'
            f'<td>{esc(entry["reason"])}</td><td>{esc(LABELS.get(entry["domain"],entry["domain"]))}</td><td>{esc(LABELS.get(entry["severity"],entry["severity"]))}</td>'
            f'<td>{esc(entry["first_seen"])}</td><td>{esc(entry["last_seen"])}</td><td>{esc(LABELS.get(entry["state"],entry["state"]))}</td>'
            f'<td>{esc(", ".join(entry.get("metrics",[])))}</td><td>{esc(entry.get("action"))}</td></tr>')
    filters=''
    for key,label in [('symbol','Société'),('source','Source'),('domain','Domaine'),('severity','Gravité')]:
        values=sorted({str(x.get(key) or '') for x in journal['entries'].values()})
        filters+=f'<label>{label}<select data-anomaly-filter="{key}"><option value="">Tous</option>'+''.join(
            f'<option value="{esc(v)}">{esc(LABELS.get(v,v))}</option>' for v in values)+'</select></label>'
    continuity=report.get('continuity') or {}
    watch='<p>Dernière observation du contrôle de continuité : '+esc(continuity.get('checked_at'))+'. <a href="continuite.json">Éditions attendues, exécutions et rattrapages</a>.</p>'
    return ('<main><section class="panel"><h1>Surveillance des anomalies</h1>'
        '<p>Un blocage local suspend les sorties concernées. Une défaillance critique globale conserve le dernier site sain. '
        'La disparition d’une observation ou une panne de source ne résout pas un incident.</p>'
        +watch+'<p><a href="anomalies.json">Journal et historique JSON</a> · <a href="couverture.json">Couverture des 80 sociétés</a></p>'
        '<div class="filters">'+filters+'</div><p data-anomaly-count></p><div class="tablewrap"><table>'
        '<thead><tr><th>Titre</th><th>Problème</th><th>Domaine</th><th>Gravité</th><th>Première détection</th>'
        '<th>Dernière détection</th><th>Statut</th><th>Conséquence</th><th>Action</th></tr></thead><tbody>'
        +''.join(rows)+'</tbody></table></div></section></main>')


def global_failure(path, now, kind, reason):
    from .market import atomic_json
    journal=json.loads(path.read_text()) if path.exists() else {'schema_version':1,'entries':{}}
    identity='global_'+sha256((kind+reason).encode()).hexdigest()[:18]
    old=journal['entries'].get(identity)
    if old:old.update(last_seen=now,state='persistent',occurrences=old['occurrences']+1)
    else:journal['entries'][identity]=dict(id=identity,symbol='GLOBAL',name='Intégrité du site',domain='publication',
        code=kind,reason=reason,severity='critical_global',source='Nour',metrics=['publication'],
        action='Corriger le défaut global avant une nouvelle publication ; dernier site complet conservé.',
        state='new',first_seen=now,last_seen=now,occurrences=1,resolutions=[])
    journal['checked_at']=now
    atomic_json(path,journal)


def resolve_global_controls(journal, now, commit):
    """Called only after all build integrity gates, before atomic replacement."""
    for entry in journal['entries'].values():
        if entry['domain']=='publication' and entry['severity']=='critical_global' and entry['state']!='resolved':
            entry.update(state='resolved',resolved_at=now)
            entry.setdefault('resolutions',[]).append(dict(at=now,generator_commit=commit,
                proof='Nouvelle génération complète : contrats financiers, statistiques, sectoriels, marché et exports contrôlés.',
                scope='build_integrity_checked_deployment_not_yet_attested'))
    journal['active_count']=sum(x['state']!='resolved' for x in journal['entries'].values())
    return journal
