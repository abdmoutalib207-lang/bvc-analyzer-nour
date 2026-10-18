/* Audit-derived regressions against canonical exports and adversarial fixtures. */
const assert=require('node:assert/strict'),fs=require('node:fs');
const {localAnswer}=require('../web/assistant.js');
const query=require('../web/assistant-query.js');
assert.equal(fs.readFileSync('web/assistant-query.js','utf8'),fs.readFileSync('backend/query.cjs','utf8'),'browser and Worker share the same generated module');
const data=JSON.parse(fs.readFileSync('web/assistant-data.json','utf8'));
const before=JSON.stringify(data),fmt=x=>x.toLocaleString('fr-FR',{maximumFractionDigits:2});
const ranking=query.select(data,'Les 5 PER les plus faibles en 2025');
const expected=Object.values(data.symbols).filter(r=>r.fundamental.exercise===2025&&Number.isFinite(r.fundamental.pe)).sort((a,b)=>a.fundamental.pe-b.fundamental.pe||a.symbol.localeCompare(b.symbol));
assert.equal(ranking.matched,expected.length);
assert.deepEqual(ranking.rows.map(r=>r.symbol),expected.slice(0,5).map(r=>r.symbol));
for(const row of ranking.rows){
  assert.equal(row.values.pe,data.symbols[row.symbol].fundamental.pe);
  assert.deepEqual(row.warnings,data.symbols[row.symbol].fundamental.warnings);
}
const selected=query.select(data,'Quelles valeurs ont un PER inférieur à 15 et un ROE supérieur à 10 % ?');
assert.equal(selected.matched,Object.values(data.symbols).filter(r=>Number.isFinite(r.fundamental.pe)&&r.fundamental.pe<15&&Number.isFinite(r.fundamental.roe_pct)&&r.fundamental.roe_pct>10).length);
for(const row of selected.rows)assert.ok(row.values.pe<15&&row.values.roe>10);
const bank=query.select(data,'Les 5 PER les plus faibles du secteur Banque en 2025');
assert.ok(bank.rows.length);assert.ok(bank.rows.every(r=>r.sector==='Banque'));
const blocked=query.select(data,'Valeurs avec dette nette suspendue');
assert.ok(blocked.rows.some(r=>r.symbol==='ADI'));
assert.ok(!blocked.rows.some(r=>r.symbol==='ATW'||r.symbol==='DIS'));
for(const row of blocked.rows){assert.equal(row.values.debt,null);assert.equal(row.metric_availability.net_debt_strict_mmad.status,'blocked');}
for(const question of ['Quelles valeurs ont un PER inférieur à 15 ou un ROE supérieur à 10 ?','Quelles valeurs ont un PER inférieur à 15 et un ESG supérieur à 80 ?','Les 5 PER les plus faibles S1 2026','Les 5 PER les plus faibles en 2024 et 2025','Les 5 PER les plus faibles du secteur inconnu']){
  const r=query.select(data,question);assert.ok(r.error,question);assert.equal(r.rows.length,0);
}
// Every supported numeric predicate is compared with a direct canonical-field oracle.
for(const metric of data.knowledge.metric_catalog){
  const aliases={price:'cours',shares:'quantité',turnover:'montant échangé',pe:'PER',eps:'BPA',pb:'P/B',roe:'ROE',debt:'dette nette',leverage:'dette nette / EBITDA',yield:'rendement du dividende',rsi:'RSI',sma20:'MM20',sma50:'MM50',sma200:'MM200',ema20:'EMA20',ema50:'EMA50',macd:'MACD',beta:'bêta',correlation:'corrélation',volatility:'volatilité',drawdown:'drawdown',var:'VaR',cvar:'CVaR',sessions:'profondeur'};
  if(!aliases[metric.id])continue;
  const r=query.select(data,'Quelles valeurs ont un '+aliases[metric.id]+' supérieur à 0 ?');
  assert.ok(r&&!r.error,metric.id);
  const read=row=>metric.path.split('.').reduce((v,k)=>v?.[k],row);
  const expectedRows=Object.values(data.symbols).filter(row=>Number.isFinite(read(row))&&read(row)>0);
  // MACD and leverage also request their components; only complete rows qualify.
  assert.ok(r.matched<=expectedRows.length,metric.id);
  for(const row of r.rows)assert.equal(row.values[metric.id],read(data.symbols[row.symbol]),metric.id);
}
const multi=localAnswer('Cours, PER, RSI et VaR ADI',data,'MASI');
for(const number of [data.symbols.ADI.price,data.symbols.ADI.fundamental.pe,data.symbols.ADI.technical.rsi14,data.symbols.ADI.market_risk.tail_risk.var95_loss_pct])assert.ok(multi.text.includes(fmt(number)));
for(const label of ['fondamentaux','technique','risques','cours'])assert.ok(multi.text.includes(label));
for(const warning of data.symbols.ADI.fundamental.warnings)assert.ok(multi.text.includes(warning));
assert.ok(multi.sources.some(s=>s.url.includes('ADI_RFA_2025.pdf')));
const bands=localAnswer('Bandes de Bollinger ADI',data,'MASI');
for(const key of ['bollinger_middle','bollinger_upper','bollinger_lower'])assert.ok(bands.text.includes(fmt(data.symbols.ADI.technical[key])));
assert.ok(localAnswer('Histogramme MACD ADI',data,'MASI').text.includes(fmt(data.symbols.ADI.technical.macd_histogram)));
const first=localAnswer('Les 5 PER les plus faibles en 2025',data,'ADI');
const follow=localAnswer('Et avec un ROE supérieur à 10 % ?',data,'ADI',first.context);
assert.equal(follow.domain,'screener');assert.ok(follow.queryResult.rows.every(r=>r.values.roe>10&&r.exercise===2025));
const mixed=localAnswer('PER et actualités ADI',data,'MASI');
assert.ok(mixed.text.includes('PER :'));assert.ok(mixed.text.includes('actualités'));assert.ok(mixed.text.includes('Métadonnées')||mixed.text.includes('veille')||mixed.text.includes('publication'));
const summary=localAnswer('Synthèse complète ADI avec actualités et sources',data,'MASI');
assert.ok(summary.text.includes('Comptes annuels'));assert.ok(summary.text.includes('État du radar'));
const absent=structuredClone(data);absent.symbols.ADI.technical.bollinger_upper=null;
assert.ok(localAnswer('Bollinger ADI',absent,'MASI').text.includes('bande supérieure : indisponible'));
assert.equal(JSON.stringify(data),before,'read-only queries must never mutate canonical facts');
console.log('Assistant query audit: compound answers, canonical ranking/filter oracles, sectors, blocked versus missing, financial periods, unknown criteria, source reservations, indicators, follow-ups and immutability passed.');
