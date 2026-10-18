/* Read-only selection of already calculated facts. Published to web/ by the builder. */
(function(root){
  'use strict';
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const value=(row,path)=>path.split('.').reduce((v,k)=>v?.[k],row);
  const numeric=x=>typeof x==='number'&&Number.isFinite(x);
  function metrics(question,catalog){const q=norm(question);return catalog.filter(m=>new RegExp('\\b(?:'+m.pattern+')').test(q));}
  function plan(question,catalog){
    const q=norm(question);let found=metrics(q,catalog);
    if(found.some(m=>m.id==='macd')){const chosen=/histogramme/.test(q)?'histogram':/signal/.test(q)?'signal':'macd';found=found.filter(m=>!['macd','signal','histogram'].includes(m.id)||m.id===chosen);}
    if(!/quell?e?s?(?: sont)?(?: les)? (?:valeurs|titres|societes|entreprises|actions)|(?:affiche|montre|cherche|recherche|trouve|donne).*(?:valeurs|titres|societes|entreprises|actions)|liste|classement|classer|filtr|palmares|top\s*\d*|les\s+\d+|(?:valeurs|titres|societes|entreprises|actions) (?:avec|ayant|dont|qui ont)|toute la cote/.test(q))return null;
    if(!found.length)return null;
    const years=[...new Set(q.match(/\b20\d{2}\b/g)||[])];
    const missing=/indisponibl|manquant|suspend|absent|non (?:calcula|rapproch)/.test(q);
    const p={metrics:found.map(m=>m.id),filters:[],missing,blocked:/suspend|bloqu/.test(q),year:years[0]?Number(years[0]):null,sort:null,limit:5,error:null};
    if(p.blocked)p.missing=true;
    const indicator=q.match(/\brsi\s*(\d+)\b/);if(indicator&&Number(indicator[1])!==14)p.error='Seul le RSI 14 est disponible dans ce relevé ; aucun autre RSI n’est déduit.';
    if(/\bou\b|\bs[12]\b|semestr|ttm|prevision|normalise/.test(q)||years.length>1)p.error='Ce filtre exige une période ou une logique non prise en charge. Utilisez des critères annuels reliés par « et », avec un seul exercice.';
    const requested=q.match(/(?:top\s*|les\s+)(\d+)\b/);if(requested)p.limit=Math.max(1,Math.min(20,Number(requested[1])));
    for(const m of found){
      const re=new RegExp('\\b(?:'+m.pattern+')\\s*(?:(?:est|soit|annuel|annuelle)\\s*)?(inferieur(?:e)?(?:s)? a|superieur(?:e)?(?:s)? a|au moins|au plus|moins de|plus de|<=|>=|<|>|=)\\s*(-?\\d+(?:[.,]\\d+)?)');
      const match=q.match(re);if(match){const op=/inferieur|moins de|^<$/.test(match[1])?'<':/superieur|plus de|^>$/.test(match[1])?'>':/au moins|>=/.test(match[1])?'>=':/au plus|<=/.test(match[1])?'<=':'=';p.filters.push({id:m.id,op,value:Number(match[2].replace(',','.'))});
        const unit=q.slice(match.index+match[0].length).match(/^\s*(%|mmad\b|mdh\b|mad\b|milliards?\b|millions?\b|points?\b|x\b)/)?.[1];
        if(unit&&(unit==='mdh'?'mmad':unit)!==norm(m.unit))p.error='Unité du seuil incompatible : '+m.label+' utilise '+(m.unit||'une valeur sans unité')+'. Aucun changement d’unité automatique.';
        if(/^\s*(?:[\d.,]|e[+-]?\d)/.test(q.slice(match.index+match[0].length)))p.error='Nombre ambigu : utilisez un nombre sans séparateur de milliers, avec une virgule ou un point décimal.';
      }
    }
    if(/plus (?:faibles?|bas|petits?)|\bcroissant\b/.test(q))p.sort={id:found[0].id,direction:'asc'};
    else if(/plus (?:eleves?|hauts?|grands?|forts?)|\bdecroissant\b/.test(q))p.sort={id:found[0].id,direction:'desc'};
    if(p.missing&&p.sort)p.error='Un ratio indisponible ou bloqué ne peut pas être classé par valeur. Demandez la liste des données absentes sans tri numérique.';
    if(/meilleur/.test(q))p.error='Un ratio ne définit pas les meilleurs titres. Précisez un seuil ou un ordre croissant ou décroissant.';
    if(/entre\s+-?\d|compris|au.dessus|au.dessous|sous (?:la |les )?(?:mm|ema|sma)|surachet|survend/.test(q))p.error='Ce critère relatif ou cet intervalle n’est pas pris en charge. Précisez un seuil numérique explicite sur une mesure.';
    if(/classement|palmares|top\b|les\s+\d+/.test(q)&&!p.sort&&!missing)p.error='Précisez le classement : par exemple « les 5 PER les plus faibles en 2025 ».';
    const operators=q.match(/[<>]=?|inferieur(?:e)?s? a|superieur(?:e)?s? a|au moins|au plus|moins de|plus de|=/g)||[];
    if(operators.length!==p.filters.length)p.error='Critère numérique non reconnu : utilisez par exemple « PER inférieur à 15 et ROE supérieur à 10 % ».';
    return p;
  }
  const proofKeys={pe:['resultat_net_part_groupe','resultat_net','nombre_actions'],eps:['resultat_net_part_groupe','resultat_net','nombre_actions'],pb:['capitaux_propres_part_groupe','capitaux_propres','nombre_actions'],roe:['resultat_net_part_groupe','resultat_net','capitaux_propres_part_groupe','capitaux_propres']};
  function select(data,question){
    const catalog=data.metric_catalog||data.knowledge?.metric_catalog||[],p=plan(question,catalog);if(!p)return null;
    const result={...p,rows:[],matched:0,excluded_missing:0,excluded_period:0,universe:Object.keys(data.symbols||{}).length};
    if(p.error)return result;
    const definitions=catalog.filter(m=>p.metrics.includes(m.id)),fin=definitions.some(m=>m.domain==='fundamentals');
    if(p.year&&!fin){result.error='Les classements techniques ou de risque à un exercice historique ne sont pas reconstruits. Retirez l’année pour consulter le dernier relevé daté.';return result;}
    const q=norm(question),sectors=[...new Set(Object.values(data.symbols||{}).map(r=>r.sector))].filter(s=>s&&new RegExp('\\b'+norm(s)+'s?\\b').test(q));
    if(/secteur|banques?|assuran|immobilier|industr|mines|technolog|telecom|agroaliment|construct|materiaux|transport|energie|finance|holding|tourisme|distribution|automobile|sante/.test(q)&&sectors.length!==1){result.error='Précisez un seul secteur du référentiel Nour, par exemple « secteur Banque » ou « secteur Immobilier ».';return result;}
    result.sector=sectors[0]||null;
    const compare=(x,f)=>f.op==='<'?x<f.value:f.op==='>'?x>f.value:f.op==='<='?x<=f.value:f.op==='>='?x>=f.value:x===f.value;
    for(const [symbol,row] of Object.entries(data.symbols||{}).sort(([a],[b])=>a.localeCompare(b))){
      if(result.sector&&row.sector!==result.sector)continue;
      if(p.year&&fin&&row.fundamental?.exercise!==p.year){result.excluded_period++;continue;}
      const values=Object.fromEntries(definitions.map(m=>[m.id,numeric(value(row,m.path))?value(row,m.path):null]));
      const absent=Object.values(values).some(v=>v===null);
      if(p.blocked&&!definitions.some(m=>row.fundamental?.metric_availability?.[m.path.split('.').at(-1)]?.status==='blocked'))continue;
      if(p.missing?!absent:absent){if(!p.missing)result.excluded_missing++;continue;}
      if(!p.filters.every(f=>numeric(values[f.id])&&compare(values[f.id],f)))continue;
      const f=row.fundamental||{};
      result.rows.push({symbol,name:row.name,sector:row.sector,url:row.url,asof:row.asof,price_source:row.price_source,
        exercise:f.exercise,period_end:f.period_end,currency:f.currency,accounting_basis:f.accounting_basis,
        validation_status:f.validation_status??null,values,warnings:fin?f.warnings||[]:[],latest_report:fin?f.latest_report||null:null,
        document_url:f.document_url??null,evidence:Object.fromEntries(Object.entries(f.evidence||{}).filter(([key])=>definitions.some(m=>(proofKeys[m.id]||[]).includes(key)))),metric_availability:fin?f.metric_availability||{}:{},
        history_readiness:row.history_readiness,collection_conflicts:row.collection_conflicts||[],
        risk_window:definitions.some(m=>m.domain==='risk')?row.market_risk:null});
    }
    if(p.sort)result.rows.sort((a,b)=>(p.sort.direction==='asc'?1:-1)*(a.values[p.sort.id]-b.values[p.sort.id])||a.symbol.localeCompare(b.symbol));
    result.matched=result.rows.length;result.rows=result.rows.slice(0,p.limit);
    result.notice='Sélection descriptive des chiffres publiés par Nour, avec réserves ; aucune recommandation. Les périmètres, devises et dates peuvent différer : ce classement ne constitue pas une comparaison sectorielle validée. Les valeurs absentes ne valent jamais zéro.';
    return result;
  }
  const format=(v,u='')=>numeric(v)?v.toLocaleString('fr-FR',{maximumFractionDigits:2})+(u?' '+u:''):'indisponible';
  function renderSelection(result,data){
    const catalog=data.knowledge?.metric_catalog||data.metric_catalog||[],defs=catalog.filter(m=>result.metrics.includes(m.id));
    const lines=[`Données Nour · analyse du ${data.analysis_date}.`,result.error||`${result.matched} titre(s) correspondant(s) sur ${result.universe}${result.sector?' · secteur '+result.sector:''} ; ${result.rows.length} affiché(s). Exclus pour donnée absente : ${result.excluded_missing} ; exercice différent ou absent : ${result.excluded_period}.`],sources=[];
    if(!result.error){
      lines.push('Critères appliqués : '+[...result.filters.map(f=>(catalog.find(m=>m.id===f.id)?.label||f.id)+' '+f.op+' '+f.value),result.year?'exercice '+result.year:null,result.sector?'secteur '+result.sector:null,result.blocked?'ratio bloqué':result.missing?'donnée indisponible':null,result.sort?'tri '+(catalog.find(m=>m.id===result.sort.id)?.label||result.sort.id)+' '+(result.sort.direction==='asc'?'croissant':'décroissant'):null].filter(Boolean).join(' · '));
      lines.push(result.notice);for(const r of result.rows){
      lines.push(`${r.symbol} · ${r.name} · clôture ${r.asof||'indisponible'} · exercice ${r.exercise||'indisponible'} · ${r.currency||'devise non renseignée'} · ${r.accounting_basis||'périmètre non renseigné'}\n`+defs.map(m=>m.label+' : '+format(r.values[m.id],m.unit)).join(' · '));
      if(r.validation_status)lines.push('Vérification : '+r.validation_status+' ; rapport entier non certifié automatiquement.');
      for(const w of r.warnings)lines.push('Réserve '+r.symbol+' : '+w);
      if(r.latest_report)lines.push('Dernière publication distincte : '+r.latest_report.period_end+' · '+(r.latest_report.accounting_basis||'périmètre non renseigné')+' · '+(r.latest_report.validation_status||'statut non renseigné')+(r.latest_report.note?' · '+r.latest_report.note:''));
      for(const m of defs){const status=r.metric_availability[m.path.split('.').at(-1)];if(status&&status.status!=='available')lines.push(m.label+' · '+status.status+' · '+(status.reason_codes||[]).join(', '));}
      if(r.history_readiness?.label)lines.push(r.history_readiness.label);
      for(const c of r.collection_conflicts)lines.push(`Collecte ${r.symbol} : conflit ${c.session} sur ${(c.fields||[]).join(', ')} ; historique conservé.`);
      if(r.risk_window)lines.push('Risque : '+[r.risk_window.first,r.risk_window.last,r.risk_window.note,r.risk_window.tail_risk?.note].filter(Boolean).join(' · '));
      sources.push({label:'Fiche '+r.symbol+' · '+r.asof,url:r.url});if(r.document_url)sources.push({label:r.symbol+' · comptes annuels',url:r.document_url});
      for(const [key,e] of Object.entries(r.evidence))if(Number.isInteger(e.page)&&e.page>0&&(e.document_url||r.document_url))sources.push({label:r.symbol+' · '+key+' · page PDF '+e.page,url:(e.document_url||r.document_url).split('#')[0]+'#page='+e.page});
    }}
    return {text:lines.join('\n\n'),sources,symbols:['MASI'],domain:'screener',mode:'local',queryResult:result};
  }
  function facts(question,data,symbols){
    const catalog=data.knowledge?.metric_catalog||[],found=metrics(question,catalog),q=norm(question);
    // Existing period-aware and explanatory routes retain annual/semester/historical handling.
    if(!found.length||symbols.includes('MASI')||/\b20\d{2}\b|semestr|\bs[12]\b|ttm|prevision|normalise|pourquoi|comment|explique|methode|calcul|compare|comparaison/.test(q))return null;
    if(found.some(m=>m.domain==='fundamentals'))return null;
    if(found.every(m=>m.domain==='risk'))return null;
    if(found.every(m=>['macd','signal','histogram'].includes(m.id))&&!/histogramme|signal/.test(q))return null;
    if(found.length<2&&!/bollinger|histogramme/.test(q))return null;
    const lines=[`Données Nour · analyse du ${data.analysis_date}.`],sources=[];
    for(const s of symbols){const r=data.symbols[s];if(!r)continue;
      lines.push(`${s} · ${r.name} · clôture ${r.asof} · source ${r.price_source||'indisponible'}.`);
      for(const m of found)lines.push(`${m.label} : ${format(value(r,m.path),m.unit)}.`);
      if(found.some(m=>m.domain==='risk'))lines.push('Risque : '+[r.market_risk?.first,r.market_risk?.last,r.market_risk?.note,r.market_risk?.tail_risk?.note].filter(Boolean).join(' · '));
      if(found.some(m=>m.domain==='technical'))lines.push('Indicateurs descriptifs sur les séances validées ; aucune prévision. Méthode : '+(r.technical?.methods?.version||'consulter la fiche')+'.');
      sources.push({label:'Fiche '+s+' · '+r.asof,url:r.url});
    }
    return {text:lines.join('\n\n'),sources,symbols,domain:found.some(m=>m.domain==='fundamentals')?'fundamentals':'technical',mode:'local'};
  }
  const api={metrics,plan,select,renderSelection,facts};
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.NourAssistantQuery=api;
})(typeof window==='object'?window:null);
