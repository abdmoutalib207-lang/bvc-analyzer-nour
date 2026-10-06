/* Exploratory historical scenarios; the canonical score is never replayed. */
(function (root) {
  'use strict';
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const net = (r, buy, sell, slip) => 100 * (r.exit * (1-(sell+slip)/100) / (r.entry*(1+(buy+slip)/100)) - 1);
  const quantile = (xs, p) => {
    if (!xs.length) return null;
    const a = xs.slice().sort((x,y)=>x-y), at=(a.length-1)*p, i=Math.floor(at);
    return a[i]+(a[Math.min(i+1,a.length-1)]-a[i])*(at-i);
  };
  function select(rows, f) {
    return rows.filter(r=>r.symbol===f.symbol && r.horizon===f.horizon &&
      (f.period==='all'||r.period===f.period) && (f.regime==='all'||r.regime===f.regime));
  }
  function summary(rows, buy, sell, slip) {
    const values=rows.map(r=>net(r,buy,sell,slip));
    const excess=rows.map((r,i)=>values[i]-r.masi_pct);
    return {count:values.length, median:quantile(values,.5), p10:quantile(values,.1), p90:quantile(values,.9),
      positive:values.length ? 100*values.filter(x=>x>0).length/values.length:null, excess:quantile(excess,.5)};
  }
  const api={net, quantile, select, summary};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  const doc=root.document;
  if (!doc || !doc.getElementById('research-lab')) return;
  const get=id=>doc.getElementById(id), data=JSON.parse(get('lab-data').textContent);
  const help=get('lab-help'), helpClose=get('lab-help-close');
  if(help && helpClose){
    const closeHelp=()=>{help.open=false;get('lab-help-toggle').focus();};
    helpClose.hidden=false;
    helpClose.addEventListener('click',closeHelp);
    help.addEventListener('keydown',event=>{
      if(event.key==='Escape' && help.open){event.preventDefault();closeHelp();}
    });
  }
  const fmt=x=>finite(x)?x.toLocaleString('fr-FR',{maximumFractionDigits:2,minimumFractionDigits:2}):'—';
  function element(tag, text, cls) {
    const e=doc.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e;
  }
  function table(headers, rows) {
    const t=element('table'), head=element('thead'), hr=element('tr'), body=element('tbody');
    headers.forEach(h=>hr.appendChild(element('th',h))); head.appendChild(hr); t.appendChild(head);
    rows.forEach(row=>{const tr=element('tr');row.forEach(x=>tr.appendChild(element('td',x)));body.appendChild(tr);});
    t.appendChild(body); return t;
  }
  function render() {
    const f={symbol:get('lab-symbol').value,horizon:Number(get('lab-horizon').value),period:get('lab-period').value,regime:get('lab-regime').value};
    const costs=['buy','sell','slip'].map(k=>Number(get('lab-'+k).value));
    if (costs.some(x=>!finite(x)||x<0||x>10) || ['buy','sell','slip'].some(k=>get('lab-'+k).value.trim()==='')) {
      get('lab-status').textContent='Renseignez des coûts entre 0 et 10 % par côté.';
      ['lab-metrics','lab-distribution','lab-periods','lab-rows','lab-audit'].forEach(id=>get(id).replaceChildren()); return;
    }
    const rows=select(data.rows,f), s=summary(rows,...costs);
    get('lab-status').textContent=`${f.symbol} · ${f.horizon} séances · ${s.count} observations. `+
      (s.count<30?'Échantillon insuffisant (< 30) ; aucune interprétation de fréquence.':'Étude rétrospective exploratoire ; les fréquences ne prédisent pas demain.');
    const metrics=get('lab-metrics');metrics.replaceChildren();
    [['Observations',s.count],['Médiane nette',fmt(s.median)+' %'],['Fréquence positive',fmt(s.positive)+' %'],
      ['Percentiles 10 / 90',fmt(s.p10)+' / '+fmt(s.p90)+' %'],['Écart médian au MASI brut',fmt(s.excess)+' points']].forEach(([label,value])=>{
        const card=element('div',undefined,'metric');card.appendChild(element('span',label));card.appendChild(element('strong',String(value)));metrics.appendChild(card);
      });
    const audit=data.audit.find(x=>x.symbol===f.symbol&&x.horizon===f.horizon);
    get('lab-audit').textContent=audit?`Grille entière avant filtres : ${audit.candidates} fenêtres candidates ; ${audit.observed} tendances observées ; ${audit.no_trend} sans tendance ; ${audit.missing} avec séances manquantes ; ${audit.event_boundary} aux frontières de capital/reprise ; ${audit.inactive} exclues pour suspension actuelle.`:'';
    const dist=get('lab-distribution');dist.replaceChildren();
    const values=rows.map(r=>net(r,...costs));
    if(values.length){
      const edges=[-Infinity,-10,-5,0,5,10,Infinity];
      const bins=edges.slice(0,-1).map((lo,i)=>({label:i===0?'≤ −10 %':i===5?'> 10 %':`${lo} à ${edges[i+1]} %`, n:values.filter(x=>x>lo&&x<=edges[i+1]).length}));
      const max=Math.max(1,...bins.map(b=>b.n));
      bins.forEach(b=>{const bar=element('div',undefined,'distribution-bin');
        bar.appendChild(element('span',b.label));const fill=element('div',undefined,'distribution-fill');fill.style.width=(100*b.n/max)+'%';fill.setAttribute('aria-label',`${b.label} : ${b.n} observations`);
        bar.appendChild(fill);bar.appendChild(element('strong',String(b.n)));dist.appendChild(bar);});
    }
    const periodRows=['2023-2024','2025+'].map(p=>{const z=summary(rows.filter(r=>r.period===p),...costs);
      return [p,String(z.count),fmt(z.median),fmt(z.excess),z.count<30?'Insuffisant (< 30)':'Descriptif'];});
    get('lab-periods').replaceChildren(table(['Période au signal','Observations','Médiane nette (%)','Écart MASI brut (points)','Échantillon'],periodRows));
    const body=get('lab-rows');body.replaceChildren();
    rows.slice(-60).forEach(r=>{const tr=element('tr');[r.signal_date,r.entry_date,r.exit_date,fmt(r.gross_pct),fmt(net(r,...costs)),fmt(r.masi_pct),fmt(net(r,...costs)-r.masi_pct)].forEach(x=>tr.appendChild(element('td',x)));body.appendChild(tr);});
  }
  ['symbol','horizon','period','regime','buy','sell','slip'].forEach(k=>get('lab-'+k).addEventListener('input',render));
  render();
})(typeof window==='undefined'?globalThis:window);
