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
console.log('Assistant: 320 title/topic scenarios, report parity, date lookup, missing values and safe links passed.');
