/* Explanatory layer only. No scoring, order, storage or provider key access. */
(function(root){
  'use strict';
  const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const fmt=(x,unit='')=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('fr-FR',{maximumFractionDigits:2})+(unit?' '+unit:''):'indisponible';
  const validationLabel=status=>{
    if(typeof status==='string'&&status.startsWith('referenced_import'))return 'référence documentaire importée, vérification indépendante non attestée';
    if(typeof status==='string'&&status.startsWith('selected_pages_reconciled_with_reservations'))return 'pages sélectionnées rapprochées, avec réserves';
    if(typeof status==='string'&&status.startsWith('selected_pages_visually_checked'))return 'pages sélectionnées vérifiées visuellement, rapport entier non certifié';
    return 'niveau de vérification à consulter dans la fiche';
  };
  const validURL=(url,prefix='')=>{
    if(typeof url!=='string')return null;
    if(/^https:\/\//i.test(url)){try{const u=new URL(url);return u.username||u.password?null:u.href;}catch{return null;}}
    return /^(?:index|recherche|macro|briefing|actualites)\.html$/.test(url)||/^titres\/[A-Z0-9]{2,5}\.html$/.test(url)?prefix+url:null;
  };
  function symbolsFor(question,data,fallback,allowFallback=true){
    let q=' '+normalize(question).replace(/\s+/g,' ')+' ';
    const found=[], common=new Set(['les','car','dis','dar']);
    const originalWords=String(question).match(/[A-Za-z0-9]+/g)||[];
    // Full issuer names take precedence: the word Dar in RDS is not ticker DAR.
    const entries=Object.entries(data.symbols||{}).sort((a,b)=>b[1].name.length-a[1].name.length);
    for(const [s,row] of entries){const name=normalize(row.name);
      if(name.length>=5&&q.includes(' '+name+' ')){found.push(s);q=q.replace(' '+name+' ',' ');}}
    const aliases={adi:'alliances',rds:'dar saada',msa:'marsa maroc',cash:'cash plus',mgl:'maghrebail',mrl:'maroc leasing',mdp:'med paper'};
    for(const [s,name] of Object.entries(aliases))if(data.symbols?.[s.toUpperCase()]&&q.includes(' '+name+' ')){
      found.push(s.toUpperCase());q=q.replace(' '+name+' ',' ');
    }
    const words=q.match(/[a-z0-9]+/g)||[];
    if(words.includes('masi'))found.push('MASI');
    for(const s of Object.keys(data.symbols||{})){
      if(words.includes(s.toLowerCase())&&(!common.has(s.toLowerCase())||originalWords.includes(s)))found.push(s);
    }
    return [...new Set(found.length?found:allowFallback?[fallback||'MASI']:[])];
  }
  function datesIn(question){
    return [...String(question).matchAll(/\b(20\d{2}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}\/(?:20\d{2}|\d{2}))\b/g)].map(m=>{
      const p=m[0].split('/'),date=p.length===3?`${p[2].length===2?'20'+p[2]:p[2]}-${p[1].padStart(2,'0')}-${p[0].padStart(2,'0')}`:m[0];
      const parsed=new Date(date+'T00:00:00Z');
      return {date,valid:Number.isFinite(parsed.getTime())&&parsed.toISOString().slice(0,10)===date};
    });
  }
  const dateIn=question=>datesIn(question).find(d=>d.valid)?.date||null;
  // Explicit, read-only intents. Values are copied from the published report.
  // A missing intent or fact is stated; it never becomes a recommendation.
  function preciseAnswer(question,data,symbols){
    const q=normalize(question), sources=[],lines=[`Données Nour · analyse du ${data.analysis_date}.`];
    const result=()=>({text:lines.join('\n\n'),sources,symbols,mode:'local'});
    if(symbols.length>2){lines.push('Comparez au maximum deux titres par question.');return result();}
    const ignored=new Set(['MASI','PER','PE','PB','BPA','ROE','ROIC','ROI','RSI','MACD','ATR','PNB','CA','RNPG','EBITDA','MAD','DH','MDH','MMAD','MM','USD','EUR','VIX','DXY','CAC','API','LLM','IA','S1','S2','PDF','TVA']);
    const unknown=(question.match(/\b[A-Z][A-Z0-9]{1,5}\b/g)||[]).filter(s=>!ignored.has(s)&&!/^(MM|SMA|RSI)\d+$/.test(s)&&!data.symbols?.[s]&&!Object.values(data.symbols||{}).some(row=>normalize(row.name).split(/\W+/).includes(normalize(s))));
    if(unknown.length){lines.push(`Titre ou abréviation non reconnu : ${[...new Set(unknown)].join(', ')}. Précisez le nom ou le symbole; le contexte sélectionné n’a pas été utilisé à sa place.`);return result();}
    const dates=datesIn(question);
    if(dates.some(d=>!d.valid)){lines.push('Date invalide : '+dates.filter(d=>!d.valid).map(d=>d.date).join(', ')+'. Utilisez une date réelle, au format JJ/MM/AAAA.');return result();}
    if(dates.length>6){lines.push('Limitez la question à six dates.');return result();}
    if(/collecte|mise a jour|actualis|fraicheur/.test(q)){
      const r=data.runtime||{};
      lines.push(`Dernière construction : ${r.built_at||'indisponible'} · édition ${r.label||r.slot||'indisponible'}. Horaire visé : ${r.target_time||'indisponible'} (${r.timezone||'Africa/Casablanca'}) · retard constaté : ${fmt(r.delay_minutes,'minutes')}.`);
      lines.push('Collectes programmées les jours ouvrés à 09:45, 11:46, 13:45, 15:45 et 18:00, heure de Casablanca. Le lancement GitHub peut être retardé; ce n’est pas un flux temps réel.');
      if(r.run_url)sources.push({label:'Dernière collecte',url:r.run_url});sources.push({label:'Tableau de bord · fraîcheur',url:'index.html'});return result();
    }
    if(/laboratoire/.test(q)&&!/probabil|demain|prochaine/.test(q)){
      lines.push('Le laboratoire rejoue une règle simple sur les anciennes séances. Vous choisissez un titre, une durée et des frais; il compte les cas et affiche les résultats obtenus dans le passé. Le bouton « ? » explique les étapes. Une fréquence passée ne dit pas ce qui se passera demain.');
      sources.push({label:'Laboratoire · aide et résultats',url:'recherche.html'});return result();
    }
    const macros=(data.macro?.groups||[]).flatMap(g=>g.rows||[]);
    const macroNames=[[/\bbrent\b|petrole/,'Brent'],[/\bcuivre\b/,'Cuivre'],[/\bcharbon\b/,'Charbon'],[/\bvix\b/,'VIX'],[/\bdxy\b|indice dollar/,'Indice dollar'],[/usd\s*\/\s*mad|dollar.*dirham/,'USD/MAD'],[/eur\s*\/\s*mad|euro.*dirham/,'EUR/MAD'],[/s&p|sp ?500/,'S&P 500'],[/cac\s*40/,'CAC 40'],[/dow jones/,'Dow Jones'],[/nikkei/,'Nikkei'],[/\bor\b.*(?:cours|prix|futures)|(?:cours|prix).*\bor\b/,'Or']];
    const requestedMacro=macroNames.filter(([pattern])=>pattern.test(q)).map(([,name])=>name);
    if(requestedMacro.length){
      if(dates.length){lines.push('Cet export contient les dernières observations internationales, pas leur historique à la date demandée.');return result();}
      for(const name of requestedMacro){const row=macros.find(x=>x.name.includes(name));
        if(!row){lines.push(`${name} : observation indisponible.`);continue;}
        lines.push(`${row.name} : ${fmt(row.value,row.unit)} · variation ${fmt(row.change_pct,'%')} · observation ${row.observed_at||'non datée'} · état ${row.state||'indisponible'} · ${row.notice||'délai à consulter dans la source'}.`);
        if(row.source_url)sources.push({label:row.name+' · '+row.source,url:row.source_url});
      }lines.push('Contexte international seulement; aucun effet calculé sur le score de Nour.');return result();
    }
    const entity=q.match(/\b(?:per|rsi|cours|prix|bpa|roe|roic)\s+(?:de\s+|du\s+|pour\s+)?([a-z][a-z ]+)[?.!]*$/)?.[1]?.trim();
    if(entity&&!symbolsFor(question,data,null,false).length&&!/^(?:son|sa|ce|cette|mon|le|la|aujourd|actuel|global|marche|place)\b/.test(entity)){
      lines.push(`Je n’ai pas identifié le titre « ${entity} ». Précisez son symbole ou sélectionnez-le dans le contexte.`);return result();
    }
    const metrics=[
      [/\bper\b|\bpe\b|cours.*benefice/,'PER','pe','', 'fundamental'],
      [/\bbpa\b/,'BPA','eps_mad','MAD','fundamental'],
      [/\bp\s*\/\s*b\b|\bpb\b/,'P/B','pb','','fundamental'],
      [/\broe\b/,'ROE','roe_pct','%','fundamental'],
      [/rendement.*dividende/,'Rendement du dividende','dividend_yield_pct','%','fundamental'],
      [/dette nette.*(?:ebitda|ebe)/,'Dette nette / EBITDA','net_debt_ebitda','','fundamental'],
      [/dette nette(?!.*(?:ebitda|ebe))/,'Dette nette stricte','net_debt_strict_mmad','MDH','fundamental'],
      [/\bpnb\b|produit net bancaire/,'PNB','pnb_mmad','MDH','fundamental'],
      [/\brsi\b|\brsi\s*14\b/,'RSI 14','rsi14','','technical'],
      [/\b(?:mm|sma)\s*20\b|moyenne mobile\s*20/,'MM20','sma20','MAD','technical'],
      [/\b(?:mm|sma)\s*50\b|moyenne mobile\s*50/,'MM50','sma50','MAD','technical'],
      [/\b(?:mm|sma)\s*200\b|moyenne mobile\s*200/,'MM200','sma200','MAD','technical'],
      [/\bmacd\b/,'MACD','macd','MAD','technical'],
      [/\batr\b/,'ATR 14 (moyenne simple)','atr14','MAD','technical'],
      [/support/,'Support descriptif sur 20 séances précédentes','support20','MAD','technical'],
      [/resistan/,'Résistance descriptive sur 20 séances précédentes','resistance20','MAD','technical'],
      [/\bbeta\b/,'Bêta historique','beta','','market_risk'],
      [/correlation/,'Corrélation historique au MASI','correlation','','market_risk']
    ].filter(([pattern])=>pattern.test(q));
    const prospective=/demain|prochaine|predi|va (?:monter|baisser)|dois.je (?:acheter|vendre)/.test(q);
    const volume=/volume|capitaux echanges|quantite|combien.*titres echanges/.test(q);
    const earnings=/rnpg|resultat|benefice/.test(q)&&!/cours.*benefice/.test(q);
    const shares=/nombre.*actions|combien.*actions|denominateur/.test(q);
    const equity=/capitaux propres|fonds propres/.test(q);
    const unsupported=/\broic\b|\broi\b|objectif.*cours|prix cible/.test(q);
    const close=/cloture|\bcours\b|\bprix\b/.test(q);
    if(!metrics.length&&!dates.length&&!volume&&!earnings&&!shares&&!equity&&!unsupported&&!close)return null;
    if(prospective||/probabil|statist|frequen/.test(q))return null;
    for(const s of symbols){
      if(s==='MASI'){
        const m=data.market||{},h=data.masi_history||{};
        lines.push(`MASI · séance ${m.masi?.asof||m.asof||'non datée'}.`);
        if(dates.length)for(const {date} of dates)lines.push(Object.hasOwn(h,date)?`Clôture du ${date} : ${fmt(h[date],'points')}.`:`Aucune clôture MASI disponible au ${date}. Aucun cours n’est interpolé.`);
        else if(close)lines.push(`Clôture : ${fmt(m.masi?.value,'points')} · variation ${fmt(m.masi?.change_pct,'%')}.`);
        if(volume){
          if(dates.some(d=>d.date!==m.asof))lines.push('Le volume global à cette date n’est pas disponible dans cet export.');
          else{lines.push(`Volume global : ${fmt(m.turnover_mad,'MAD')} · ${fmt(m.shares,'titres échangés')} · ${fmt(m.transactions,'transactions')}.`);
            const a=data.market_volume_audit||{};lines.push(`Rapprochement des lignes de la séance : ${a.status==='matched'?'totaux concordants':a.status==='discrepancy'?'écart constaté':'couverture non confirmée'} · ${a.observed_lines??'—'} / ${a.expected_lines??'—'} lignes. Les fiches anciennes sont exclues de la somme.`);}
        }
        if(metrics.length||earnings||equity||shares||unsupported)lines.push('Le PER global du marché et son historique ne sont pas intégrés dans Nour. Les autres ratios et indicateurs techniques demandés ne sont pas disponibles pour le MASI dans cet export; aucun chiffre n’est déduit du graphique.');
        sources.push({label:'MASI · données et graphique',url:'index.html'});continue;
      }
      const row=data.symbols[s];if(!row){lines.push(`Titre ${s} absent du référentiel.`);continue;}
      const f=row.fundamental||{},latest=f.latest_report||{},ev=f.evidence||{};
      lines.push(`${s} · ${row.name} · séance ${row.asof||'non datée'} · source ${row.price_source||'non précisée'}.`);
      if(row.asof!==data.analysis_date)lines.push('Attention : dernière séance du titre différente de la date d’analyse; donnée ancienne ou indisponible.');
      sources.push({label:`Fiche ${s} · ${row.asof}`,url:row.url});
      if(dates.length){
        const history=Object.fromEntries((row.close_dates_last_60||[]).map((d,i)=>[d,row.close_series_last_60?.[i]]));
        for(const {date} of dates)lines.push(Object.hasOwn(history,date)?`Clôture du ${date} : ${fmt(history[date],'MAD')}.`:`Clôture du ${date} indisponible dans cet export de 60 observations. Consultez le graphique; aucun cours n’est interpolé.`);
        if(metrics.length||earnings||equity||shares)lines.push('Les ratios et indicateurs à ces dates ne sont pas reconstruits; les valeurs actuelles ne sont pas utilisées à leur place.');
        if(volume)lines.push('Le volume à cette date n’est pas disponible dans cet export.');
        continue;
      }
      const requestedYears=[...q.matchAll(/\b(20\d{2})\b/g)].map(m=>Number(m[1]));
      const wrongYear=requestedYears.some(y=>y!==f.exercise)&&!(/semest|\bs1\b|\bs2\b/.test(q)&&earnings);
      for(const [,label,key,unit,group] of metrics){
        const value=wrongYear&&group==='fundamental'?null:row[group]?.[key];
        lines.push(`${label} : ${fmt(value,unit)}${group==='fundamental'?` · comptes annuels ${f.exercise||'indisponibles'}`:''}.`);
        if(wrongYear&&group==='fundamental')lines.push('L’exercice demandé ne correspond pas à la référence disponible; aucun ratio historique n’est reconstruit.');
        if(key==='macd')lines.push(`Signal MACD : ${fmt(row.technical?.macd_signal,'MAD')}.`);
        if(key==='eps_mad')lines.push(`Dénominateur : ${f.eps_denominator||'non vérifié'}.`);
        if(key==='net_debt_ebitda'||key==='net_debt_strict_mmad')lines.push(f.net_debt_method||'Périmètre de dette à consulter dans la fiche.');
        if(key==='roe_pct')lines.push(data.definitions.roe);
      }
      if(earnings){
        const semi=/semest|\bs1\b|\bs2\b/.test(q);
        if(semi){const isS2=/\bs2\b|deuxieme semestre/.test(q);
          const wantsGroup=/rnpg|part (?:du )?groupe/.test(q),hasGroup=/part (?:du )?groupe|rnpg/i.test(latest.reported_net_label||'');
          for(const requested of [...new Set(requestedYears.length?requestedYears:[null])]){
            const current=latest.period_end?.endsWith('-06-30')&&(!requested||latest.period_end.startsWith(String(requested)));
            const previous=latest.reported_net_previous_period_end?.endsWith('-06-30')&&requested&&latest.reported_net_previous_period_end.startsWith(String(requested));
            const ok=!isS2&&(current||previous),period=previous?latest.reported_net_previous_period_end:latest.period_end,value=previous?latest.reported_net_previous_millions:latest.reported_net_millions;
            if(ok&&wantsGroup&&!hasGroup)lines.push('Résultat net part du groupe de ce semestre : indisponible. Le résultat total publié ne le remplace pas.');
            lines.push(ok?`${latest.reported_net_label||'Résultat publié'} : ${fmt(value,'MDH')} · période ${period} · ${latest.accounting_basis||'périmètre non précisé'}${previous?' · comparatif publié dans le dernier rapport':''}.`:`Résultat de ce semestre${requested?' '+requested:''} indisponible dans cet export.`);
          }
        }else lines.push(`Résultat annuel retenu : ${fmt(wrongYear?null:f.earnings_mmad,'MDH')} · exercice ${f.exercise||'indisponible'} · ${f.accounting_basis||'périmètre non précisé'}.`);
      }
      if(equity){const e=ev.capitaux_propres_part_groupe||ev.capitaux_propres_sociaux;lines.push(`Capitaux propres : ${fmt(wrongYear?null:e?.value,'MDH')} · comptes annuels ${f.exercise||'indisponibles'} · ${e?.accounting_basis||f.accounting_basis||'périmètre non précisé'}.`);}
      if(shares){
        for(const key of ['nombre_actions_retenu_pour_le_bpa','nombre_actions_existant','nombre_actions','nombre_actions_au_rapport','nombre_actions_annuel_verifie'])if(ev[key]){
          const e=ev[key];lines.push(`Actions · ${key==='nombre_actions_retenu_pour_le_bpa'?'moyenne pondérée publiée':'référence annuelle'} : ${fmt(wrongYear?null:e.value,'actions')} · page ${e.page}. ${e.note||''}`);
        }
        if(!Object.keys(ev).some(k=>k.startsWith('nombre_actions')))lines.push('Nombre d’actions vérifié : indisponible.');
        lines.push(`BPA : ${f.eps_denominator||'dénominateur non disponible'}. Valeur comptable : ${f.book_denominator||'dénominateur non disponible'}.`);
      }
      if(volume)lines.push(`Volume de la dernière séance du titre (${row.asof||'non datée'}) : ${fmt(row.day_turnover_mad_actual,'MAD')} · ${fmt(row.day_shares,'titres échangés')}.`);
      if(close)lines.push(`Clôture : ${fmt(row.price,'MAD')}.`);
      if(unsupported)lines.push('Le ROIC, le ROI et les objectifs de cours ne sont pas calculés dans Nour. Aucune valeur n’est reprise du moteur principal comme résultat Nour.');
      if(metrics.some(m=>m[4]==='fundamental')||earnings||equity||shares){
        lines.push(`Vérification annuelle : ${validationLabel(f.validation_status)}. Le semestre n’est pas annualisé; PNB et chiffre d’affaires restent distincts.`);
        if(latest.period_end)lines.push(`Dernière publication : ${latest.period_end} · ${validationLabel(latest.validation_status)}.`);
        const warnings=[latest.note||'',...(f.warnings||[])].filter(Boolean);if(warnings.length)lines.push('Réserves à lire :\n'+warnings.join('\n'));
        if(f.document_url)sources.push({label:`${s} · comptes annuels`,url:f.document_url});
        if(latest.document_url)sources.push({label:`${s} · dernière publication`,url:latest.document_url});
      }
      if(metrics.some(m=>m[4]==='technical'))lines.push('Les niveaux décrivent les observations disponibles; ils ne valident pas une probabilité de franchissement ou de maintien.');
      if(/(?:apres|au.dessus|au.dessous|a partir).*?\d/.test(q))lines.push('Aucun scénario conditionnel n’a été calculé au seuil mentionné dans votre question; les niveaux ci-dessus sont ceux de la fiche publiée.');
    }
    return result();
  }
  function localAnswer(question,data,fallback){
    const q=normalize(question), symbols=symbolsFor(question,data,fallback), sources=[];
    const precise=preciseAnswer(question,data,symbols);if(precise)return precise;
    const lines=[`Données Nour · analyse du ${data.analysis_date}.`];
    const probability=/probabil|statist|frequen|prochaine|demain|predi|acheter|vendre/.test(q);
    const fundamental=/fondament|\bper\b|\bbpa\b|\bp\/b\b|\broe\b|resultat|benefice|semestre|dette|pnb|capital/.test(q);
    const score=/score|note/.test(q);
    const macro=/macro|international|petrole|brent|devis|dollar|s&p|cac 40|dow jones|nikkei/.test(q);
    if(!probability&&!fundamental&&!score&&!macro&&!/resume|resum|bilan|synthese|historique|masi/.test(q))return {
      text:`Données Nour · analyse du ${data.analysis_date}.\n\nJe ne reconnais pas assez précisément cette question. Précisez le titre et la mesure, par exemple « PER JET », « RSI ADI », « volume global MASI » ou « MASI le 31/03/2026 ».`,sources:[],symbols,mode:'local'};
    if(macro){
      for(const group of data.macro?.groups||[])for(const row of group.rows||[]){
        lines.push(`${row.name} : ${fmt(row.value,row.unit)} · observation ${row.observed_at||'non datée'} · état ${row.state||'indisponible'}.`);
        if(row.source_url)sources.push({label:row.name+' · '+row.source,url:row.source_url});
      }
      if(!(data.macro?.groups||[]).length)lines.push('Observations internationales indisponibles.');
      lines.push('Les dates et délais diffèrent selon les marchés. Aucune causalité ni influence sur le score n’est déduite de ces observations.');
      sources.push({label:'Macro / International',url:'macro.html'});
      return {text:lines.join('\n\n'),sources,symbols,mode:'local'};
    }
    for(const s of symbols){
      if(s==='MASI'){
        const m=data.market?.masi||{}, hist=data.masi_history||{}, dates=Object.keys(hist).sort(), d=dateIn(question);
        lines.push(`MASI : ${fmt(m.value,'points')} · séance ${m.asof||data.market?.asof||'non datée'} · variation ${fmt(m.change_pct,'%')}.`);
        lines.push(`Historique disponible : ${dates[0]||'—'} → ${dates.at(-1)||'—'} · ${dates.length} séances.`);
        if(d)lines.push(Object.hasOwn(hist,d)?`Clôture du ${d} : ${fmt(hist[d],'points')}.`:`Aucune clôture MASI disponible au ${d}. Aucun cours n’est interpolé.`);
        if(probability||/support|resistan/.test(q))lines.push('Un ancien niveau peut servir de zone à examiner. Nour ne dispose pas ici d’une probabilité validée de tenue du support à la prochaine séance. Le laboratoire permet d’explorer des fréquences historiques, avec effectifs et frais.');
        if(fundamental)lines.push('Le MASI est un indice : pas de BPA, de bénéfice part du groupe ou de PER d’entreprise dans cette fiche.');
        if(score)lines.push('Aucun score prospectif MASI validé n’est disponible. L’historique de cours ne constitue pas un historique de scores publiés.');
        sources.push({label:'MASI · données et graphique',url:'index.html'},{label:'Laboratoire historique',url:'recherche.html'});
        continue;
      }
      const row=data.symbols[s];
      if(!row){lines.push(`Le titre ${s} est absent du référentiel Nour.`);continue;}
      const f=row.fundamental||{}, t=row.technical||{}, cs=row.canonical_score||{}, latest=f.latest_report||{};
      lines.push(`${s} · ${row.name}\nClôture : ${fmt(row.price,'MAD')} · séance ${row.asof||'non datée'} · source ${row.price_source||'non précisée'}. Statut des données : ${row.decision||'indisponible'}.`);
      if(fundamental){
        lines.push(`Comptes annuels ${f.exercise||'indisponibles'} · ${f.accounting_basis||'périmètre non précisé'} · ${validationLabel(f.validation_status)}.\nBPA : ${fmt(f.eps_mad,'MAD')} · PER : ${fmt(f.pe)} · P/B : ${fmt(f.pb)} · ROE : ${fmt(f.roe_pct,'%')}.\nDette nette / EBITDA : ${fmt(f.net_debt_ebitda)} · PNB : ${fmt(f.pnb_mmad,'MDH')}.`);
        if(latest.period_end)lines.push(`Dernière publication : ${latest.period_end} · ${latest.accounting_basis||'périmètre non précisé'}.\n${latest.reported_net_label||'Résultat publié'} : ${fmt(latest.reported_net_millions,'millions '+(latest.currency||'MAD'))}.\nVérification : ${validationLabel(latest.validation_status)} · pages ${latest.pages||'non renseignées'}.`);
        const warnings=[latest.note||'',...(f.warnings||[])].filter(Boolean);
        if(warnings.length)lines.push('Réserves à lire :\n'+warnings.join('\n'));
        lines.push('Un ratio absent reste indisponible. Le semestre n’est pas annualisé; PNB et chiffre d’affaires restent distincts.');
      }else if(probability){
        const stats=row.historical_statistics||{}, horizons=stats.horizons||[];
        for(const h of horizons)lines.push(`${h.horizon_sessions} séance(s) : ${h.observations} observations · fréquence de rendements positifs ${fmt(h.positive_frequency_pct,'%')} · médiane ${fmt(h.median_return_pct,'%')} · état ${h.state}.`);
        lines.push(stats.note||data.definitions.probability);
      }else if(score){
        lines.push(`Score descriptif : ${fmt(cs.value)} / 100 · couverture ${fmt(cs.coverage_pct,'%')} · état ${cs.state||'indisponible'} · version ${cs.version||'—'}.`);
        for(const [name,c] of Object.entries(cs.contributors||{}))lines.push(`${name} : ${fmt(c.points)} points / poids ${fmt(c.weight)}.`);
        lines.push(data.definitions.score);
      }else{
        lines.push(`Score descriptif : ${fmt(cs.value)} / 100 · ${cs.state||'indisponible'}.\nRSI 14 : ${fmt(t.rsi14)} · MM20 : ${fmt(t.sma20,'MAD')}.\nSupport / résistance descriptifs : ${fmt(t.support20)} / ${fmt(t.resistance20)} MAD.\nPER annuel : ${fmt(f.pe)} · dette nette / EBITDA : ${fmt(f.net_debt_ebitda)}.`);
        lines.push('Les niveaux techniques décrivent les séances disponibles; ils ne prédisent aucune trajectoire.');
      }
      sources.push({label:`Fiche ${s} · ${row.asof}`,url:row.url});
      if(fundamental){if(f.document_url)sources.push({label:`${s} · comptes annuels`,url:f.document_url});if(latest.document_url)sources.push({label:`${s} · dernière publication`,url:latest.document_url});}
    }
    if(probability)lines.push(data.definitions.probability);
    if(!fundamental&&!probability&&!score&&symbols.length===1)lines.push('Questions reconnues : résumé, fondamentaux, score, statistiques, macro et clôture MASI à une date. Pour une explication libre, un LLM doit être configuré.');
    return {text:lines.join('\n\n'),sources,symbols,mode:'local'};
  }
  const api={localAnswer,symbolsFor,dateIn,datesIn,validURL};
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(!root?.document)return;
  const doc=root.document, dialog=doc.getElementById('assistant-dialog');
  if(!dialog)return;
  const el=id=>doc.getElementById('assistant-'+id), prefix=dialog.dataset.prefix||'';
  let data=null, loading=null, config={endpoint:null}, busy=false, controller=null, generation=0;
  function message(role,text,sources=[],mode='local'){
    const box=doc.createElement('article');box.className='assistant-message';box.dataset.role=role;
    const label=doc.createElement('small');label.textContent=role==='user'?'Vous':mode==='llm'?'Explication IA · à vérifier avec les sources':'Nour · lecture des données';
    const p=doc.createElement('p');p.textContent=text;box.append(label,p);
    if(sources.length){const links=doc.createElement('div');links.className='assistant-sources';
      const seen=new Set();for(const source of sources){const url=validURL(source.url,prefix);if(!url||seen.has(url))continue;seen.add(url);
        const a=doc.createElement('a');a.href=url;a.textContent=source.label;if(url.startsWith('https:')){a.target='_blank';a.rel='noopener noreferrer';}links.append(a);}box.append(links);}
    el('messages').append(box);box.scrollIntoView({block:'start'});
  }
  async function loadData(){
    if(data)return;
    el('status').textContent='Chargement des données datées…';
    const response=await root.fetch(prefix+'assistant-data.json',{cache:'no-cache'});
    if(!response.ok)throw new Error('Données de l’assistant indisponibles. Les fiches restent consultables.');
    const snapshot=await response.json();
    if(snapshot.schema_version!=='nour-assistant-data-v1'||!snapshot.symbols)throw new Error('Format des données non reconnu.');
    data=snapshot;
    for(const [s,row] of Object.entries(data.symbols)){const option=doc.createElement('option');option.value=s;option.textContent=`${s} · ${row.name}`;el('symbol').append(option);}
    const current=root.location.pathname.match(/\/titres\/([A-Z0-9]{2,5})\.html$/)?.[1];
    if(current&&data.symbols[current])el('symbol').value=current;
    try{const res=await root.fetch(prefix+'assistant-config.json',{cache:'no-cache'});if(res.ok)config=await res.json();}
    catch{config={endpoint:null};}
    if(config.endpoint&&(/^(?:\/api\/assistant|api\/assistant)$/.test(config.endpoint)||/^https:\/\//.test(config.endpoint))){
      el('ai-option').hidden=false;el('ai-label').textContent=`Utiliser l’IA (${config.provider_label||'fournisseur configuré'}) : envoyer la question et les données sélectionnées. Aucune clé dans le navigateur.`;
    }else config.endpoint=null;
    message('assistant',`Données chargées · analyse du ${data.analysis_date}. Choisissez un titre ou posez une question sur le MASI. Les réponses locales suivent des règles explicites; elles ne sont pas générées par une IA.`);
    el('status').textContent='Conversation conservée uniquement en mémoire dans cette page.';
  }
  function load(){
    if(loading)return loading;
    loading=loadData().catch(error=>{loading=null;throw error;});
    return loading;
  }
  function resetBusy(){busy=false;el('send').disabled=false;el('symbol').disabled=false;el('ai').disabled=false;}
  async function submit(question){
    if(busy)return;question=question.trim();if(!question)return;
    if(question.length>1200){el('status').textContent='Question limitée à 1 200 caractères.';return;}
    busy=true;el('send').disabled=true;el('symbol').disabled=true;el('ai').disabled=true;
    const epoch=generation;
    try{
      await load();message('user',question);el('question').value='';
      const answer=localAnswer(question,data,el('symbol').value);
      if(answer.symbols.length===1&&(answer.symbols[0]==='MASI'||data.symbols[answer.symbols[0]]))el('symbol').value=answer.symbols[0];
      if(el('ai').checked&&config.endpoint){
        el('status').textContent='Explication IA en cours…';controller=new AbortController();const timeout=setTimeout(()=>controller?.abort(),35000);
        let res;try{res=await root.fetch(config.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'omit',signal:controller.signal,
          body:JSON.stringify({question,symbols:answer.symbols,consent:true})});}finally{clearTimeout(timeout);}
        const result=await res.json();if(!res.ok||result.mode!=='llm'||typeof result.text!=='string')throw new Error(result.error||'Le fournisseur IA n’a pas répondu.');
        if(epoch!==generation)return;
        message('assistant',result.text,result.sources||answer.sources,'llm');
        message('assistant','Référence chiffrée Nour (distincte du texte IA) :\n\n'+answer.text,answer.sources);
      }else if(epoch===generation)message('assistant',answer.text,answer.sources);
      if(epoch===generation)el('status').textContent='Réponse datée. Consultez les sources et réserves avant toute décision.';
    }catch(error){if(epoch===generation){message('assistant',error.name==='AbortError'?'Délai IA dépassé. Désactivez le mode IA pour lire les données locales.':error.message);el('status').textContent='Réponse indisponible; aucun chiffre n’a été inventé.';}}
    finally{if(epoch===generation){controller=null;resetBusy();if(dialog.open)el('question').focus();}}
  }
  el('open').hidden=false;
  el('open').addEventListener('click',async()=>{dialog.showModal();el('question').focus();try{await load();}catch(error){message('assistant',error.message);el('status').textContent='Chargement impossible.';}});
  el('close').addEventListener('click',()=>dialog.close());
  el('clear').addEventListener('click',()=>{generation++;controller?.abort();controller=null;resetBusy();el('messages').replaceChildren();el('question').value='';el('status').textContent='Conversation effacée de cette page.';el('question').focus();});
  el('form').addEventListener('submit',event=>{event.preventDefault();submit(el('question').value);});
  el('ai').addEventListener('change',()=>{el('mode').textContent=el('ai').checked?'IA d’explication · sources Nour':'Lecture des données · sans IA générative';});
  for(const button of doc.querySelectorAll('[data-assistant-question]'))button.addEventListener('click',()=>submit(button.dataset.assistantQuestion));
})(typeof window==='undefined'?null:window);
