/* Explanatory layer only. No scoring, order, storage or provider key access. */
(function(root){
  'use strict';
  const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const fmt=(x,unit='')=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('fr-FR',{maximumFractionDigits:2})+(unit?' '+unit:''):'indisponible';
  const validURL=(url,prefix='')=>{
    if(typeof url!=='string')return null;
    if(/^https:\/\//i.test(url)){try{const u=new URL(url);return u.username||u.password?null:u.href;}catch{return null;}}
    return /^(?:index|recherche|macro|briefing|actualites)\.html$/.test(url)||/^titres\/[A-Z0-9]{2,5}\.html$/.test(url)?prefix+url:null;
  };
  function symbolsFor(question,data,fallback){
    let q=' '+normalize(question).replace(/\s+/g,' ')+' ';
    const found=[], common=new Set(['les','car','dis','dar']);
    const originalWords=String(question).match(/[A-Za-z0-9]+/g)||[];
    // Full issuer names take precedence: the word Dar in RDS is not ticker DAR.
    const entries=Object.entries(data.symbols||{}).sort((a,b)=>b[1].name.length-a[1].name.length);
    for(const [s,row] of entries){const name=normalize(row.name);
      if(name.length>=5&&q.includes(' '+name+' ')){found.push(s);q=q.replace(' '+name+' ',' ');}}
    const words=q.match(/[a-z0-9]+/g)||[];
    if(words.includes('masi'))found.push('MASI');
    for(const s of Object.keys(data.symbols||{})){
      if(words.includes(s.toLowerCase())&&(!common.has(s.toLowerCase())||originalWords.includes(s)))found.push(s);
    }
    return [...new Set(found.length?found:[fallback||'MASI'])].slice(0,2);
  }
  function dateIn(question){
    let m=question.match(/\b(20\d\d)-(\d\d)-(\d\d)\b/);
    if(m)return m[0];
    m=question.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{2}|20\d{2})\b/);
    return m?`${m[3].length===2?'20'+m[3]:m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`:null;
  }
  function localAnswer(question,data,fallback){
    const q=normalize(question), symbols=symbolsFor(question,data,fallback), sources=[];
    const lines=[`Données Nour · analyse du ${data.analysis_date}.`];
    const probability=/probabil|statist|frequen|prochaine|demain|predi|acheter|vendre/.test(q);
    const fundamental=/fondament|\bper\b|\bbpa\b|\bp\/b\b|\broe\b|resultat|benefice|semestre|dette|pnb|capital/.test(q);
    const score=/score|note/.test(q);
    const macro=/macro|international|petrole|brent|devis|dollar|s&p|cac 40|dow jones|nikkei/.test(q);
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
        lines.push(`Comptes annuels ${f.exercise||'indisponibles'} · ${f.accounting_basis||'périmètre non précisé'} · statut ${f.validation_status||'non vérifié'}.\nBPA : ${fmt(f.eps_mad,'MAD')} · PER : ${fmt(f.pe)} · P/B : ${fmt(f.pb)} · ROE : ${fmt(f.roe_pct,'%')}.\nDette nette / EBITDA : ${fmt(f.net_debt_ebitda)} · PNB : ${fmt(f.pnb_mmad,'MDH')}.`);
        if(latest.period_end)lines.push(`Dernière publication : ${latest.period_end} · ${latest.accounting_basis||'périmètre non précisé'}.\n${latest.reported_net_label||'Résultat publié'} : ${fmt(latest.reported_net_millions,'millions '+(latest.currency||'MAD'))}.\nStatut : ${latest.validation_status||'non vérifié'} · pages ${latest.pages||'non renseignées'}.`);
        const warnings=[...(f.warnings||[]),latest.note||''].filter(Boolean);
        if(warnings.length)lines.push('Réserves à lire :\n'+warnings.slice(0,3).join('\n'));
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
  const api={localAnswer,symbolsFor,dateIn,validURL};
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
    el('messages').append(box);el('messages').scrollTop=el('messages').scrollHeight;
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
