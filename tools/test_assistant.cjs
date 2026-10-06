/* No network/provider calls: deterministic answers, dates, absent data and URL safety. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const api=require('../web/assistant.js');
const data=JSON.parse(fs.readFileSync('web/assistant-data.json','utf8'));
let answer=api.localAnswer('Explique le PER de JET',data,'MASI');
assert.deepEqual(answer.symbols,['JET']);
assert.ok(answer.text.includes(data.symbols.JET.fundamental.pe.toLocaleString('fr-FR',{maximumFractionDigits:2})));
assert.ok(answer.text.includes(data.symbols.JET.asof));
assert.ok(answer.sources.some(s=>s.url===data.symbols.JET.fundamental.document_url));
assert.ok(answer.text.includes('semestre n’est pas annualisé'));
assert.ok(answer.text.includes(data.symbols.JET.fundamental.latest_report.note));
assert.ok(!answer.text.includes('selected_pages_reconciled_'));
assert.ok(answer.text.includes('pages sélectionnées rapprochées, avec réserves'));
answer=api.localAnswer('Quelle probabilité pour ADI demain ?',data,'MASI');
assert.ok(answer.text.includes('n’est pas une probabilité de prochaine séance'));
assert.ok(answer.text.includes('observations'));
assert.ok(!answer.text.includes('ACHETER'));
answer=api.localAnswer('MASI le 31/03/26',data,'MASI');
assert.ok(answer.text.includes('2026-03-31'));
assert.ok(answer.text.includes(data.masi_history['2026-03-31'].toLocaleString('fr-FR',{maximumFractionDigits:2})));
answer=api.localAnswer('MASI le 2026-09-17',data,'MASI');
assert.ok(answer.text.includes('Aucune clôture MASI disponible'));
answer=api.localAnswer('Quel support demain pour le MASI ?',data,'MASI');
assert.ok(answer.text.includes('pas ici d’une probabilité validée'));
assert.deepEqual(api.symbolsFor('Compare Alliances et Résidences Dar Saada',data,'MASI').sort(),['ADI','RDS']);
assert.deepEqual(api.symbolsFor('Dis moi les probabilités car je veux comprendre',data,'MASI'),['MASI']);
assert.deepEqual(api.symbolsFor('Explique LES',data,'MASI'),['LES']);
for(const s of Object.keys(data.symbols)){
  for(const q of ['résumé','fondamentaux','score','statistiques']){
    const r=api.localAnswer(q,data,s);assert.ok(r.text.includes(s));assert.ok(r.text.includes(data.symbols[s].asof));
    assert.ok(r.sources.some(source=>source.url===`titres/${s}.html`));assert.equal(r.mode,'local');
  }
}
assert.equal(api.validURL('javascript:alert(1)'),null);
assert.equal(api.validURL('//evil.test'),null);
assert.equal(api.validURL('https://user:secret@evil.test'),null);
assert.equal(api.validURL('../private.json'),null);
assert.equal(api.validURL('titres/ADI.html','../'),'../titres/ADI.html');
assert.equal(api.dateIn('25/02/25'),'2025-02-25');
assert.equal(api.dateIn('31/03/2026'),'2026-03-31');
const missing=structuredClone(data);missing.symbols.JET.fundamental.pe=null;
assert.ok(api.localAnswer('PER JET',missing,'JET').text.includes('PER : indisponible'));
const f=x=>typeof x==='number'?x.toLocaleString('fr-FR',{maximumFractionDigits:2}):'indisponible';
const scenarios=[
  ['Quel RSI de ADI ?',r=>r.text.includes('RSI 14 : '+f(data.symbols.ADI.technical.rsi14))&&!r.text.includes('PER :')],
  ['MM50 ADI',r=>r.text.includes('MM50 : '+f(data.symbols.ADI.technical.sma50))&&!r.text.includes('MM20 :')],
  ['MM200 JET',r=>r.text.includes('MM200 : '+f(data.symbols.JET.technical.sma200))],
  ['MACD ADI',r=>r.text.includes('Signal MACD : '+f(data.symbols.ADI.technical.macd_signal))],
  ['Compare le PER de ADI et RDS',r=>r.symbols.length===2&&r.text.includes('PER : '+f(data.symbols.ADI.fundamental.pe))&&r.text.includes('PER : '+f(data.symbols.RDS.fundamental.pe))],
  ['Quel volume global MASI ?',r=>r.text.includes(f(data.market.turnover_mad))&&r.text.includes('titres échangés')&&r.text.includes('totaux concordants')],
  ['Volume JET',r=>r.text.includes(f(data.symbols.JET.day_turnover_mad_actual))&&r.text.includes(f(data.symbols.JET.day_shares))],
  ['MASI le 11/03/26 et le 31/03/26',r=>['2026-03-11','2026-03-31'].every(d=>r.text.includes(f(data.masi_history[d])))],
  ['MASI le 31/02/26',r=>r.text.includes('Date invalide')&&!r.text.includes('Clôture du')],
  ['Clôture JET le '+data.symbols.JET.asof,r=>r.text.includes(f(data.symbols.JET.price))],
  ['Clôture JET le 2024-01-02',r=>r.text.includes('indisponible dans cet export')],
  ['Pourquoi le PER CIH est indisponible ?',r=>r.text.includes('PER : indisponible')&&r.text.includes('Capital')],
  ['RNPG JET S1 2026',r=>r.text.includes(f(data.symbols.JET.fundamental.latest_report.reported_net_millions))&&r.text.includes('Réserves à lire')],
  ['RNPG JET S1 2025',r=>r.text.includes(f(data.symbols.JET.fundamental.latest_report.reported_net_previous_millions))&&r.text.includes('période 2025-06-30')&&r.text.includes('comparatif publié')],
  ['RNPG JET S1 2024',r=>r.text.includes('Résultat de ce semestre 2024 indisponible')],
  ['RNPG M2M S1 2026',r=>r.text.includes('Résultat net part du groupe de ce semestre : indisponible')&&r.text.includes('total (minoritaires compris)')],
  ['ROIC JET',r=>r.text.includes('ne sont pas calculés dans Nour')&&!r.text.includes('10,2')],
  ['PER global MASI',r=>r.text.includes('PER global du marché et son historique ne sont pas intégrés')],
  ['Cours de tesla',r=>r.text.includes('Je n’ai pas identifié le titre')&&!r.text.includes('Clôture :')],
  ['PER ZZZ',r=>r.text.includes('non reconnu')&&!r.text.includes('Clôture :')],
  ['Quel prix du Brent ?',r=>r.text.includes('Brent')&&!r.text.includes('Nikkei')],
  ['Quand a lieu la collecte ?',r=>r.text.includes('09:45')&&r.text.includes('retard constaté')],
  ['Je cherche mon mot de passe',r=>r.text.includes('Je ne reconnais pas assez précisément')&&!r.text.includes('Score descriptif')],
  ['Compare ADI JET RDS',r=>r.text.includes('au maximum deux titres')],
  ['PER JET 2024',r=>r.text.includes('PER : indisponible')&&r.text.includes('exercice demandé')],
  ['ADI support après 336 dh',r=>r.text.includes('Aucun scénario conditionnel')&&r.text.includes('Support descriptif')],
  ['Combien d’actions JET ?',r=>r.text.includes(f(data.symbols.JET.fundamental.evidence.nombre_actions_au_rapport.value))&&r.text.includes('Valeur NON lue au rapport')],
  ['Capitaux propres CASH',r=>r.text.includes(f(data.symbols.CASH.fundamental.evidence.capitaux_propres_part_groupe.value))&&r.text.includes('comptes annuels')],
  ['Brent le 2025-01-02',r=>r.text.includes('pas leur historique à la date demandée')],
];
for(const [question,check] of scenarios)assert.ok(check(api.localAnswer(question,data,'MASI')),question);
assert.deepEqual(api.localAnswer('Et son RSI ?',data,'ADI').symbols,['ADI']);
assert.ok(api.localAnswer('Et son RSI ?',data,'ADI').text.includes('RSI 14 : '+f(data.symbols.ADI.technical.rsi14)));
console.log(`Assistant: 320 title/topic smoke scenarios + ${scenarios.length} precise-answer cases, follow-up context, report parity, missing values and safe links passed.`);
