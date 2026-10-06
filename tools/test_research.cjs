/* Formula parity, filters, small samples and real DOM control rendering. */
const assert=require('node:assert/strict');
const api=require('../web/research.js');
const rows=[
  {symbol:'MASI',horizon:20,period:'2023-2024',regime:'above',entry:100,exit:110,masi_pct:10,gross_pct:10,signal_date:'2024-01-01',entry_date:'2024-01-02',exit_date:'2024-02-01'},
  {symbol:'MASI',horizon:20,period:'2025+',regime:'below',entry:100,exit:90,masi_pct:-10,gross_pct:-10,signal_date:'2025-01-01',entry_date:'2025-01-02',exit_date:'2025-02-01'},
  {symbol:'AAA',horizon:5,period:'2025+',regime:'above',entry:100,exit:100,masi_pct:2,gross_pct:0,signal_date:'2025-01-01',entry_date:'2025-01-02',exit_date:'2025-01-09'}];
assert.ok(Math.abs(api.net({entry:100,exit:100},1,1,0)+1.9801980198)<1e-8);
assert.ok(api.net(rows[0],1,1,1)<api.net(rows[0],1,1,0));
assert.equal(api.quantile([1,2,3,4],.5),2.5);
assert.equal(api.summary([],1,1,0).median,null);
for(const symbol of ['MASI','AAA'])for(const horizon of [5,20,60])for(const period of ['all','2023-2024','2025+'])for(const regime of ['all','above','below']){
  const f={symbol,horizon,period,regime};const selected=api.select(rows,f);
  assert.ok(selected.every(r=>r.symbol===symbol&&r.horizon===horizon&&(period==='all'||r.period===period)&&(regime==='all'||r.regime===regime)));
}
class E{
  constructor(){this.children=[];this.style={};this.value='';this.textContent='';this.listeners={};}
  appendChild(e){this.children.push(e);return e;}replaceChildren(...xs){this.children=xs;}
  setAttribute(k,v){this[k]=v;}addEventListener(k,f){this.listeners[k]=f;}
}
const elements={};
const ids=['research-lab','lab-data','lab-symbol','lab-horizon','lab-period','lab-regime','lab-buy','lab-sell','lab-slip','lab-status','lab-metrics','lab-distribution','lab-audit','lab-periods','lab-rows'];
ids.forEach(id=>elements[id]=new E());
elements['lab-data'].textContent=JSON.stringify({rows,audit:[{symbol:'MASI',horizon:20,candidates:3,observed:2,missing:1,no_trend:0,event_boundary:0,inactive:0}]});
Object.entries({symbol:'MASI',horizon:'20',period:'all',regime:'all',buy:'1',sell:'1',slip:'0'}).forEach(([k,v])=>elements['lab-'+k].value=v);
global.window={document:{getElementById:id=>elements[id],createElement:()=>new E()}};
delete require.cache[require.resolve('../web/research.js')];require('../web/research.js');
assert.equal(elements['lab-rows'].children.length,2);
assert.equal(elements['lab-distribution'].children.length,6);
assert.ok(elements['lab-status'].textContent.includes('Échantillon insuffisant'));
elements['lab-period'].value='2025+';elements['lab-period'].listeners.input();assert.equal(elements['lab-rows'].children.length,1);
elements['lab-symbol'].value='AAA';elements['lab-horizon'].value='5';elements['lab-symbol'].listeners.input();assert.equal(elements['lab-rows'].children.length,1);
elements['lab-buy'].value='';elements['lab-buy'].listeners.input();assert.equal(elements['lab-rows'].children.length,0);
assert.ok(elements['lab-status'].textContent.includes('Renseignez'));
delete global.window;
console.log('Research: 108 filter scenarios, cost formulas, DOM rendering, small samples and invalid inputs passed.');
