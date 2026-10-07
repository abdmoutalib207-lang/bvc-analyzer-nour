/* Read-only answers for the implemented product. Lab arithmetic reuses its UI. */
(function(root){
  'use strict';
  const Research=typeof module==='object'&&module.exports?require('./research.js'):root.NourResearch;
  const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const finite=x=>typeof x==='number'&&Number.isFinite(x);
  const fmt=(x,u='')=>finite(x)?x.toLocaleString('fr-FR',{maximumFractionDigits:2})+(u?' '+u:''):'indisponible';
  const stateLabel=s=>({available:'disponible',insufficient:'insuffisant',historical_only:'historique uniquement',closed:'clôture',published:'publié',provisional:'provisoire',stale:'archive ancienne',unavailable:'indisponible',partial:'partiel',updated:'actualisé',unchanged:'inchangé'}[s]||s||'indisponible');
  const isMethod=question=>/explique|c.est quoi|qu.est.ce|que.*veut dire|ca veut dire|a quoi (?:sert|correspond)|signifi|definition|comment|formule|pour les nuls|difference|fonctionn/.test(normalize(question));
  const terms=[
    [/\bper\b|\bpe\b/,'per'],[/\bbpa\b/,'bpa'],[/\bp\s*\/\s*b\b|\bpb\b/,'pb'],[/\broe\b/,'roe'],[/\bpnb\b/,'pnb'],[/rnpg|part (?:du )?groupe/,'rnpg'],[/dette/,'debt'],
    [/\brsi\s*14?\b|\brsi\b/,'rsi'],[/\b(?:mm|sma)\s*\d+|moyenne mobile/,'mm'],[/macd/,'macd'],[/bollinger/,'bollinger'],[/\batr\b/,'atr'],[/support|resistan/,'levels'],[/activite/,'activity'],
    [/liquidite|capacite/,'liquidity'],[/beta/,'beta'],[/correlation/,'correlation'],[/volatil/,'volatility'],[/drawdown|baisse maximale/,'drawdown'],[/statist|frequen/,'statistics'],[/wilson|intervalle.*95/,'wilson'],[/median|percentil/,'percentile'],
    [/comparable|pairs|secteur/,'sector'],[/score|note/,'score'],[/archive|historique.*score/,'archive'],[/laboratoire|backtest/,'laboratory'],[/frais|glissement/,'costs'],[/actualite|radar/,'news'],[/macro|international/,'macro'],[/qualite|statut|suspend|reprise/,'quality'],[/intrajournal|provisoire|intraday/,'intraday'],[/collecte|actualis|mise a jour/,'collection'],[/graphique|bougie|zoom/,'chart'],[/ecc|assistant|generative|\bllm\b/,'assistant']
  ];
  function decorate(question,data,answer){
    const q=normalize(question);
    if(!isMethod(question))return answer;
    const defs=data.knowledge?.definitions||{};
    const extras=terms.filter(([p,key])=>p.test(q)&&defs[key]&&!answer.text.includes(defs[key])).slice(0,5).map(([,key])=>defs[key]);
    return extras.length?{...answer,text:answer.text+'\n\n'+extras.join('\n\n')}:answer;
  }
  function labFilters(q,previous={}){
    const filters={horizon:20,period:'all',regime:'all',buy:1,sell:1,slip:0,...previous};
    const h=q.match(/\b(\d+)\s*(?:seances?|jours?)\b/);if(h)filters.horizon=Number(h[1]);
    if(![5,20,60].includes(filters.horizon))return {error:'Le laboratoire propose 5, 20 ou 60 séances. Cet horizon n’est pas implémenté.'};
    if(/regime|au.dessus|au.dessous|sous/.test(q)&&[...q.matchAll(/\b(?:mm|sma)\s*(\d+)\b/g)].some(m=>Number(m[1])!==200))return {error:'Le filtre de régime du laboratoire utilise uniquement le MASI face à MM200. Ce régime demandé n’est pas implémenté.'};
    if(/2023\s*(?:-|a|et)\s*2024|avant 2025/.test(q))filters.period='2023-2024';
    if(/depuis 2025|2025\s*\+/.test(q))filters.period='2025+';
    const years=[...q.matchAll(/\b20\d{2}\b/g)];
    if(years.length&&!/2023\s*(?:-|a|et)\s*2024|avant 2025|depuis 2025|2025\s*\+/.test(q))return {error:'Les périodes disponibles sont tout l’historique, 2023–2024 et depuis 2025. Cette période précise n’est pas implémentée.'};
    if(/toutes? les periodes?|ensemble.*historique/.test(q))filters.period='all';
    if(/au.dessus|superieur.*mm\s*200/.test(q))filters.regime='above';
    if(/sous.*mm\s*200|au.dessous|inferieur.*mm\s*200/.test(q))filters.regime='below';
    if(/tous les regimes|sans filtre.*regime/.test(q))filters.regime='all';
    let costs=0;const seen=new Set(),keys={achat:'buy',vente:'sell',glissement:'slip'};
    const number='([+-]?\\d+(?:[.,]\\d+)?)';
    const costPattern=new RegExp('\\b(achat|vente|glissement)\\s*(?:[:=]|de|a)?\\s*'+number+'\\s*%|'+number+'\\s*%\\s*(?:a\\s+l[’\x27]?|a\\s+la|a|de|pour)?\\s*(achat|vente|glissement)\\b','g');
    for(const m of q.matchAll(costPattern)){
      const key=keys[m[1]||m[4]];if(seen.has(key))return {error:'Un coût a été indiqué plusieurs fois. Précisez une valeur unique pour achat, vente et glissement.'};
      seen.add(key);filters[key]=Number((m[2]||m[3]).replace(',','.'));costs++;
    }
    if(/sans frais|frais nuls/.test(q)){filters.buy=filters.sell=filters.slip=0;costs++;}
    if(/%/.test(q)&&/frais|achat|vente|glissement/.test(q)&&(q.match(/[+-]?\d+(?:[.,]\d+)?\s*%/g)||[]).length>costs)return {error:'Précisez chaque coût : par exemple « achat 1 %, vente 1 %, glissement 0 % ». Aucun coût ambigu n’a été appliqué.'};
    if(['buy','sell','slip'].some(k=>!finite(filters[k])||filters[k]<0||filters[k]>10))return {error:'Les coûts acceptés sont de 0 à 10 % par côté, comme dans le laboratoire.'};
    return {filters};
  }
  function answer(question,data,symbols,state={}){
    const q=normalize(question),lines=[`Données Nour · analyse du ${data.analysis_date}.`],sources=[];
    const defs=data.knowledge?.definitions||{};
    const result=(domain,extra={})=>({text:lines.join('\n\n'),sources,symbols,mode:'local',domain,...extra});
    const link=(label,url)=>sources.push({label,url});
    const definition=key=>{if(defs[key])lines.push(defs[key]);};
    const rows=symbols.filter(s=>data.symbols?.[s]).map(s=>data.symbols[s]);
    const title=row=>{lines.push(`${row.symbol} · ${row.name} · séance ${row.asof||'non datée'} · statut ${row.decision||'indisponible'}.`);link(`Fiche ${row.symbol}`,row.url);
      if(row.asof!==(data.market?.asof||data.analysis_date))lines.push('La dernière séance du titre diffère de la dernière clôture du marché; aucun chiffre n’est présenté comme une nouvelle séance.');};
    const horizon=q.match(/\b(\d+)\s*(?:seances?|jours?)\b/);
    const method=isMethod(question);
    const follow=/^(?:et\s+(?:sur|avec|si|pour)|avec|sur\s+\d|frais|glissement)/.test(q);
    if(/que.*(?:peux|sais|peut).*(?:repondre|demander|faire)|fonctionnalit|quels?.*(?:indicateurs|fonctions)|que fait.*nour|comment utiliser.*nour|tout.*implemente|capacites|questions possibles|aide.*assistant/.test(q)){
      lines.push('Je couvre les fonctions suivantes. Vous pouvez demander leur explication ou les données d’un titre, et comparer deux titres.');
      for(const c of data.knowledge?.capabilities||[])lines.push(`${c.label} : « ${c.example} »`);
      definition('assistant');definition('limits');link('Toutes les fonctions Nour','index.html');return result('navigation');
    }
    if(/difference.*(?:part.*groupe|rnpg|total)|(?:part.*groupe|rnpg|total).*difference/.test(q)&&!rows.some(row=>q.includes(row.symbol.toLowerCase()))){definition('rnpg');definition('pb');return result('fundamentals');}
    if(/archive.*(?:score|note)|historique.*(?:score|note)|performance.*score|score.*(?:efficac|valide|predict)/.test(q)){
      const a=data.score_archive||{};lines.push(`Archive prospective : ${a.daily_snapshots??'indisponible'} journée(s) · ${a.first_day||'—'} → ${a.last_day||'—'} · état ${a.status||'indisponible'}.`);
      if(a.note)lines.push(a.note);definition('archive');link('Laboratoire · suivi des scores','recherche.html');return result('score');
    }
    if(/laboratoire|backtest|replay|apres frais|tendance.*frais|regime.*mm\s*200|frais.*(?:achat|vente)|glissement/.test(q)||(state.domain==='laboratory'&&follow)){
      if(/support|resistan|\brsi\b|macd|bollinger|probabil.*(?:demain|prochaine)|fiscal|impot|dividende/.test(q)){
        lines.push('Ce scénario n’est pas implémenté : le laboratoire utilise sa règle MM20/MM50 fixe, sans stratégie RSI/MACD/Bollinger, support précis, fiscalité/dividendes ni probabilité de prochaine séance.');definition('laboratory');definition('costs');link('Laboratoire','recherche.html');return result('laboratory');
      }
      const parsed=labFilters(q,state.domain==='laboratory'?state.labFilters:{});
      if(parsed.error){lines.push(parsed.error);return result('laboratory');}
      const f=parsed.filters,r=data.research||{};
      if(!Array.isArray(r.rows)||!Research){lines.push('Résultats du laboratoire indisponibles dans cet export.');definition('laboratory');return result('laboratory');}
      if(method&&!horizon&&!/resultat|combien|median|frequen|%/.test(q)){definition('laboratory');definition('costs');lines.push('Le bouton « ? » dans le laboratoire ouvre une explication simple.');link('Laboratoire et aide','recherche.html');return result('laboratory',{labFilters:f});}
      for(const s of symbols){
        const selected=Research.select(r.rows,{...f,symbol:s}),summary=Research.summary(selected,f.buy,f.sell,f.slip);
        lines.push(`${s} · laboratoire ${f.horizon} séances · période ${f.period} · MASI au signal ${f.regime==='all'?'tous régimes':f.regime==='above'?'au-dessus de MM200':'sous MM200'} · achat ${fmt(f.buy,'%')}, vente ${fmt(f.sell,'%')}, glissement ${fmt(f.slip,'%')}.`);
        lines.push(`${summary.count} observations · médiane nette ${fmt(summary.median,'%')} · fréquence positive ${fmt(summary.positive,'%')} · percentiles 10 / 90 ${fmt(summary.p10,'%')} / ${fmt(summary.p90,'%')} · écart médian au MASI brut ${fmt(summary.excess,'points')}.`);
        if(summary.count<30)lines.push('Échantillon insuffisant (< 30) : aucune interprétation de fréquence.');
        const audit=(r.audit||[]).find(x=>x.symbol===s&&x.horizon===f.horizon);
        if(audit)lines.push(`Grille entière avant filtres : ${audit.candidates} candidats, ${audit.observed} observés, ${audit.no_trend} sans tendance, ${audit.missing} avec données manquantes, ${audit.event_boundary} aux frontières de capital/reprise, ${audit.inactive} exclus pour suspension.`);
        if(/date|dernier.*cas|exemple/.test(q))for(const x of selected.slice(-3))lines.push(`Signal ${x.signal_date} · entrée ${x.entry_date} à ${fmt(x.entry,s==='MASI'?'points':'MAD')} · sortie ${x.exit_date} à ${fmt(x.exit,s==='MASI'?'points':'MAD')} · rendement net ${fmt(Research.net(x,f.buy,f.sell,f.slip),'%')}.`);
      }
      lines.push(r.protocol||defs.laboratory);for(const limit of r.limitations||[])lines.push(limit);
      lines.push('Le résumé réutilise les mêmes filtres et formules que le laboratoire. Une fréquence historique n’est pas une probabilité de prochaine séance.');
      link('Laboratoire interactif','recherche.html');link('Observations du laboratoire','recherche.json');return result('laboratory',{labFilters:f});
    }
    if(/briefing|synthese.*(?:seance|marche)|resume.*cloture/.test(q)){
      const key=/matin/.test(q)?'briefing-matin':/midi|mi.journee/.test(q)?'briefing-midi':/fin de journee|edition.*cloture/.test(q)?'briefing-cloture':/cloture/.test(q)?'cloture':'briefing';
      const b=data.briefings?.[key];
      if(!b){lines.push('Cette édition n’est pas disponible dans l’export. Les éditions absentes ne sont pas reconstituées.');link('Briefing','briefing.html');return result('briefing');}
      const explicitDates=[...q.matchAll(/\b(20\d{2}-\d{2}-\d{2})\b/g)].map(m=>m[1]);
      if(explicitDates.some(d=>d!==b.generated_for&&d!==b.market_session)){lines.push('L’édition demandée à cette date n’est pas disponible dans cet export.');return result('briefing');}
      lines.push(`${b.title||'Briefing'} · préparé pour ${b.generated_for} · séance de référence ${b.market_session||'indisponible'} · état ${b.edition_status||'indisponible'}.`);
      if(b.edition_notice)lines.push(b.edition_notice);
      if(rows.length&&state.explicitSymbols?.some(s=>s!=='MASI')){for(const row of rows){const f=(b.focus||[]).find(x=>x.symbol===row.symbol);title(row);
        if(!f){lines.push('Ce titre n’appartient pas aux valeurs commentées dans cette édition; sa fiche reste disponible.');continue;}
        lines.push(...(f.reading?.paragraphs||[f.scenario||'Lecture indisponible.']));if(f.reading?.checkpoint)lines.push('Points sectoriels à examiner : '+f.reading.checkpoint);
      }}else{lines.push(...(b.editorial?.paragraphs||[b.market_summary||b.index_notice||'Synthèse indisponible.']));
        if(/secteur/.test(q))lines.push(...(b.editorial?.sector_paragraphs||[]));
        if(/scenario|vigilance/.test(q))lines.push(...(b.editorial?.vigilance||[]));}
      lines.push(b.limitations||'Lecture descriptive; aucune probabilité prédictive.');link('Édition source',key+'.html');if(b.text_url)link('Texte de l’édition',b.text_url);return result('briefing');
    }
    if(/actualite|radar|publication.*(?:recent|officiel)|derniere.*(?:nouvelle|publication)|presse|\bfed\b|\bbce\b|\bhcp\b|inflation|taux directeur/.test(q)&&!/semestre|resultat|rnpg|\bbpa\b/.test(q)){
      const globalNews=/global|general|international|macro|\bfed\b|\bbce\b|\bhcp\b|inflation|marche/.test(q);
      let articles=(data.news||[]).filter(a=>globalNews||!rows.length||(a.tickers||[]).some(s=>symbols.includes(s)));
      if(/officiel|ammc|primaire/.test(q))articles=articles.filter(a=>a.tier==='S1');
      for(const word of ['fed','bce','hcp','inflation'])if(new RegExp('\\b'+word+'\\b').test(q))articles=articles.filter(a=>normalize([a.title,a.publisher,a.feed_id,a.category].join(' ')).includes(word));
      const day=q.match(/\b20\d{2}-\d{2}-\d{2}\b/)?.[0];if(day)articles=articles.filter(a=>a.published_at?.startsWith(day));
      articles=articles.slice().sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at)));
      lines.push(`${articles.length} publication(s) repérée(s) dans ce périmètre; voici les ${Math.min(6,articles.length)} dernières.`);
      for(const a of articles.slice(0,6)){lines.push(`${a.title} · ${a.publisher||'source non précisée'} · ${a.published_at} · ${a.tier==='S1'?'présence officielle repérée':'alerte à recouper'} · ${a.status||'vérification non établie'}.`);link(a.title,a.url);}
      if(!articles.length)lines.push('Aucune publication dans le flux disponible ne signifie pas qu’aucune publication existe.');
      if(/inflation|taux directeur/.test(q))lines.push('Nour ne fournit pas ici un chiffre validé de taux ou d’inflation : seul le radar de sources est implémenté.');
      lines.push(`État du radar : ${data.health?.news_health?.status||'indisponible'}.`);definition('news');link('Radar complet et filtres','actualites.html');return result('news');
    }
    if(/collecte|mise a jour|actualis|fraicheur/.test(q)){
      const r=data.runtime||{};definition('collection');lines.push(`Dernière construction : ${r.built_at||'indisponible'} · démarrage ${r.started_at||'indisponible'} · édition ${r.label||r.slot||'indisponible'} · horaire visé ${r.target_time||'non programmé'} · retard constaté ${fmt(r.delay_minutes,'minutes')}.`);
      for(const [name,h] of Object.entries(data.health||{}))lines.push(`${name==='health'?'Cours':name==='overview_health'?'MASI et marché':'Radar'} : ${stateLabel(h?.result||h?.status)} · contrôle ${h?.checked_at||'non daté'}. ${h?.message||''}`);
      if(r.run_url)link('Dernière exécution',r.run_url);link('Manifestation de collecte','runtime.json');return result('quality');
    }
    if(/intraday|intrajournal|provisoire|temps reel|en direct|pendant.*seance/.test(q)){
      const i=data.intraday||{};lines.push(`Point de séance : ${i.status||'indisponible'} · séance ${i.session||'non datée'} · observation ${i.observed_at||'non datée'}. ${i.notice||''}`);
      for(const row of rows){title(row);const quote=i.status==='provisional'?row.intraday_quote:null;lines.push(quote?`Cours provisoire ${fmt(quote.price,'MAD')} · quantité ${fmt(quote.shares,'titres')} · montant ${fmt(quote.turnover_mad,'MAD')}.`:'Aucune cotation provisoire fraîche pour ce titre. La clôture n’est pas utilisée comme cours en direct.');}
      definition('intraday');link('État de séance','index.html');return result('quality');
    }
    if(/couverture|combien.*(?:titres|societes|references)|fondamentaux.*(?:correct|verifie|fiable)|manquants?/.test(q)&&!/actions|seances|liquidite/.test(q)){
      const c=data.coverage||{};lines.push(`Univers ${c.universe??'indisponible'} · références annuelles ${c.referenced??'indisponible'} · publications récentes ${c.with_recent_report??'indisponible'} · BPA ${c.with_eps??'indisponible'} · P/B ${c.with_pb??'indisponible'} · ROE ${c.with_roe??'indisponible'}.`);
      lines.push('Références annuelles manquantes : '+((c.missing_documents||[]).join(', ')||'aucune recensée')+'.');
      const all=Object.values(data.symbols||{});lines.push(`PER disponible sur ${all.filter(x=>x.fundamental?.pe!=null).length} titres. Revues annuelles de pages primaires : ${all.filter(x=>x.fundamental?.validation_status?.startsWith('selected_pages_visually_checked')).length}; autres imports à revérifier séparément.`);
      lines.push(c.interpretation||'Une référence ne certifie pas tous les ratios.');link('Données et disponibilité','index.html');return result('fundamentals');
    }
    if(/donnees.*(?:qualite|fiab|ancien|verifi)|qualite|fiabilite|suspend|reprise|(?:sources?|provenance|reservations?)\s+(?:de|du|pour)|pourquoi.*(?:limite|indisponible)/.test(q)&&!/\bper\b|\bbpa\b|\bp\/b\b|dette/.test(q)){
      for(const row of rows){title(row);const c=row.quality||{};lines.push(`Historique : ${c.usable_close_bars??'indisponible'} clôtures utilisables · âge ${fmt(row.age_calendar_days,'jours calendaires')} · ${c.invalid_open_count??0} ouvertures et ${c.invalid_close_count??0} clôtures invalides.`);
        for(const issue of c.issues||[])lines.push(issue);const f=row.fundamental||{};lines.push(`Référence annuelle ${f.exercise||'absente'} · ${f.accounting_basis||'périmètre non renseigné'} · ${f.validation_status?.startsWith('selected_pages')?'revue de pages sélectionnées, pas certification du rapport':'import documentaire, vérification indépendante non attestée'}.`);
        for(const w of f.warnings||[])lines.push(w);if(f.latest_report?.note)lines.push(f.latest_report.note);if(f.document_url)link('Document annuel '+row.symbol,f.document_url);}
      definition('quality');if(!rows.length)lines.push('Les dates, états et réserves sont affichés par titre; les statuts du marché ne certifient pas chaque dossier.');link('Qualité et sources','index.html');return result('quality');
    }
    if(/secteur.*(?:fondament|calcul|banqu|assur)|banques.*(?:btp|industrie)|method.*sector/.test(q)){definition('sectors');definition('sector');link('Points sectoriels du briefing','briefing.html');return result('fundamentals');}
    if(/comparable|\bpairs\b|mediane.*secteur|percentile.*secteur|compare.*secteur|(?:son|du|au|meme) secteur/.test(q)){
      if(!rows.length){lines.push('Sélectionnez un titre pour ses comparables comptables.');definition('sector');return result('sector');}
      for(const row of rows){title(row);const c=row.sector_comparison||{};lines.push(`Secteur ${c.sector||'indisponible'} · exercice ${c.exercise||'—'} · ${c.scope||'périmètre inconnu'} · ${c.standard||'norme inconnue'}.`);
        for(const [key,m] of Object.entries(c.metrics||{}))lines.push(`${key==='pe'?'PER':key==='pb'?'P/B':'ROE'} : titre ${fmt(m.value)} · médiane des autres ${fmt(m.median)} · percentile ${fmt(m.percentile,'/ 100')} · ${m.other_peers??0} autres pairs · état ${stateLabel(m.status)} · ${(m.symbols||[]).join(', ')||'aucun'}.`);
        lines.push(c.note||defs.sector);}
      definition('sector');return result('sector');
    }
    if(/liquidite|capacite|sortir|ecouler|median.*(?:volume|quantite)/.test(q)){
      for(const row of rows){title(row);const l=row.liquidity||{};
        lines.push(`Liquidité : ${l.ready?'estimation disponible':'insuffisante'} · ${l.active_sessions??'—'} séances actives sur ${l.window_sessions??'—'}. Quantité médiane ${fmt(l.median_shares,'titres')} · montant médian estimé ${fmt(l.median_turnover_mad_estimated,'MAD')} · médiane hors 5 plus gros montants ${fmt(l.median_turnover_ex_top5_mad_estimated,'MAD')}.`);
        lines.push(`Scénario publié : ${fmt(l.scenario_shares,'titres')} · capacité à 10 % ${fmt(l.capacity_shares_per_session_at_10pct,'titres/séance')} · délai hypothétique ${fmt(l.exit_days_at_10pct,'séances')}. ${l.post_resume_only?'Calcul restreint aux séances après reprise.':''}`);
        const requested=q.match(/\b(\d+)\s*titres\b/);if(requested&&Number(requested[1])!==l.scenario_shares)lines.push('La quantité demandée diffère du scénario publié. Aucun nouveau délai d’exécution n’est calculé par cet assistant.');}
      if(!rows.length)lines.push('Sélectionnez un titre : la liquidité par titre ne se déduit pas du volume global MASI.');definition('liquidity');return result('liquidity');
    }
    if(/risque|beta|correlation|volatil|drawdown|baisse maximale|rendement relatif|ecart.*masi/.test(q)){
      for(const row of rows){title(row);const r=row.market_risk||{};lines.push(`Risque : ${stateLabel(r.status)} · ${r.paired_returns??0} rendements appariés · minimum ${r.minimum??60} · ${r.first||'—'} → ${r.last||'—'} · fenêtre complète ${r.complete_window?'oui':'non'}.`);
        if(horizon&&!/volatil/.test(q))lines.push('Cet horizon personnalisé n’est pas fourni pour le risque. Les valeurs ci-dessous gardent leur fenêtre publiée de 253 séances MASI.');
        const metrics=[[/beta|risque/,'Bêta','beta',''],[/correlation|risque/,'Corrélation MASI','correlation',''],[/volatil|risque/,'Volatilité annualisée titre','volatility_pct','%'],[/volatil|risque/,'Volatilité MASI appariée','masi_volatility_pct','%'],[/drawdown|baisse maximale|risque/,'Baisse maximale titre','drawdown_pct','%'],[/drawdown|baisse maximale|risque/,'Baisse maximale MASI','masi_drawdown_pct','%'],[/rendement relatif|ecart|risque/,'Écart de rendement au MASI','relative_return_pp','points']];
        for(const [p,label,k,u] of metrics)if(p.test(q))lines.push(`${label} : ${fmt(r[k],u)}.`);
        if(/volatil/.test(q)&&horizon)lines.push(Number(horizon[1])===20?`Volatilité de tendance sur 20 rendements : ${fmt(row.trend?.realized_volatility_20d_pct,'%')}.`:'La volatilité sur cet horizon précis n’est pas fournie; les valeurs ci-dessus gardent leur fenêtre publiée.');
        if(r.note)lines.push(r.note);}
      if(!rows.length)lines.push('Le risque apparié au MASI se consulte par titre; aucune statistique de risque autonome MASI n’est ajoutée à cet export.');return result('risk');
    }
    if(/statist|frequen|wilson|intervalle.*95|percentil|median.*rendement/.test(q)||(state.domain==='statistics'&&follow)){
      for(const row of rows){title(row);const stat=row.historical_statistics||{};let hs=stat.horizons||[];
        if(horizon)hs=hs.filter(h=>h.horizon_sessions===Number(horizon[1]));
        if(!hs.length)lines.push('Aucune statistique de fiche disponible pour cet horizon. Les horizons implémentés sont 1, 5 et 20 observations; le laboratoire utilise une autre méthode.');
        for(const h of hs)lines.push(`${h.horizon_sessions} séance(s) : ${h.observations} observations · fréquence positive ${fmt(h.positive_frequency_pct,'%')} · médiane ${fmt(h.median_return_pct,'%')} · percentiles 10 / 90 ${fmt(h.p10_return_pct,'%')} / ${fmt(h.p90_return_pct,'%')} · Wilson 95 % ${h.wilson95_pct?h.wilson95_pct.map(x=>fmt(x,'%')).join(' à '):'indisponible'} · état ${stateLabel(h.state)}.`);
        lines.push(stat.note||defs.statistics);}
      if(!rows.length)lines.push('La fiche de fréquences inconditionnelles n’est pas calculée pour le MASI; ses études de tendances sont dans le laboratoire.');
      lines.push(data.definitions?.probability||'Une fréquence historique n’est pas une probabilité de prochaine séance.');link('Études historiques','recherche.html');return result('statistics');
    }
    if(/score|note/.test(q)){
      for(const row of rows){title(row);const s=row.canonical_score||{};lines.push(`Score descriptif : ${fmt(s.value)} / 100 · couverture ${fmt(s.coverage_pct,'%')} · état ${s.state||'indisponible'} · version ${s.version||'—'}.`);
        for(const [name,c] of Object.entries(s.contributors||{}))lines.push(`${name} : ${fmt(c.points)} points / poids ${fmt(c.weight)}.`);}
      if(!rows.length)lines.push('Aucun score MASI validé n’est fourni.');definition('score');return result('score');
    }
    if(/graphique|bougie|zoom|bollinger|curseur|courbe|chandelier|export|telecharg|\bcsv\b|\bjson\b|navigation|filtre.*(?:univers|titre)/.test(q)){
      definition('chart');
      if(/bollinger/.test(q)){definition('bollinger');if(!method)lines.push('Les valeurs numériques des bandes sont calculées dans le graphique et ne sont pas présentes dans cet export de l’assistant. Consultez le graphique; aucune valeur n’est inventée ici.');}
      if(/export|telecharg|csv|json/.test(q)){link('Rapport complet daté','report.json');link('Études JSON','recherche.json');link('Études CSV','recherche.csv');for(const row of rows)link(`Historique OHLCV ${row.symbol}`,`historique/${row.symbol}.csv`);}
      if(/filtre|navigation/.test(q))lines.push('Le tableau de marché se filtre par recherche, secteur et état des données. La fiche d’un titre affiche ses comptes, graphique, risque, comparables et sources. Les filtres du radar portent sur source/thème/périmètre/titre et ceux du laboratoire sur titre/horizon/période/régime.');
      link('Graphique et navigation',rows[0]?.url||'index.html');return result('chart');
    }
    if(/ecc|assistant|generative|\bllm\b|ollama|intelligence artificielle/.test(q)){definition('assistant');definition('limits');link('Assistant et fonctions','index.html');return result('assistant');}
    if(/smart money|carnet|spread|objectif de cours|prediction|predire/.test(q)){definition('limits');link('Données disponibles','index.html');return result('assistant');}
    if(/plus haut|plus bas|extrem|depuis.*janvier|\bytd\b|hausses|baisses|combien.*(?:hausse|baisse)|valeurs.*(?:montent|baissent)|secteurs?|amplitude|largeur.*marche|transactions|plus fortes.*(?:hausse|baisse)/.test(q)&&(!rows.length||/valeurs.*(?:montent|baissent)|hausses.*baisses|largeur.*marche/.test(q))){
      const m=data.market||{},b=m.breadth||{};lines.push(`Marché · séance ${m.asof||'non datée'} · état ${m.status||'indisponible'}.`);
      if(/plus haut|plus bas|extrem|amplitude/.test(q))lines.push(`Plus haut MASI ${fmt(m.high,'points')} · plus bas ${fmt(m.low,'points')}. Ces extrêmes ne sont pas une clôture.`);
      if(/depuis.*janvier|\bytd\b/.test(q))lines.push(`Variation MASI depuis la fin d’année précédente : ${fmt(m.masi?.ytd_pct,'%')}.`);
      if(/hausse|baisse|montent|baissent|largeur/.test(q))lines.push(`Hausses ${b.up??'—'} · baisses ${b.down??'—'} · inchangées ${b.flat??'—'} · valeurs traitées ${b.quoted??'—'}.`);
      if(/transactions/.test(q))lines.push(`Transactions : ${fmt(m.transactions)}.`);
      if(/secteur/.test(q))for(const s of m.sectors||[])lines.push(`${s.libelle} : ${fmt(s.variation_pct,'%')}.`);
      if(/plus fortes/.test(q)){const e=data.briefings?.briefing?.editorial||{};for(const key of ['leaders','laggards'])for(const x of (e[key]||[]).slice(0,3))lines.push(`${key==='leaders'?'Hausse':'Baisse'} ${x.symbol} : ${fmt(x.change_pct,'%')} · classement de l’édition ${data.briefings.briefing.market_session}.`);}
      link('Séance et secteurs','index.html');return result('market');
    }
    if(/activite|variation.*20|rendement.*20|tendance|nombre.*seances/.test(q)&&rows.length){
      for(const row of rows){title(row);const t=row.technical||{};if(/activite/.test(q))lines.push(`Activité : ${fmt(t.volume_vs_median20,'× la quantité médiane précédente')}.`);
        if(/variation|rendement|tendance/.test(q))lines.push(`Variation sur 20 séances : ${fmt(t.return20_pct,'%')} · MM20 ${fmt(t.sma20,'MAD')} · MM50 ${fmt(t.sma50,'MAD')}.`);
        if(/nombre.*seances/.test(q))lines.push(`Séances techniques : ${t.sessions??'indisponible'}.`);}
      if(/activite/.test(q))definition('activity');return result('technical');
    }
    if(method){const selected=terms.filter(([p,key])=>p.test(q)&&defs[key]);
      if(selected.length&&!rows.length){for(const [,key] of selected.slice(0,5))definition(key);link('Méthodes et données','index.html');return result('navigation');}}
    return null;
  }
  const api={answer,decorate,labFilters};
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.NourAssistantDomains=api;
})(typeof window==='undefined'?globalThis:window);
