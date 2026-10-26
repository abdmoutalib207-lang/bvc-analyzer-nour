/* Real exported facts, no model call: choices, period boundaries and explanations. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const api=require('../web/assistant.js');
const data=JSON.parse(fs.readFileSync('web/assistant-data.json','utf8'));
const original=JSON.stringify(data);
const cases=[
 ['Toutes les sociétés cotées sont-elles obligatoirement en IFRS ?',/ne signifie pas IFRS pour tous/],
 ['Quelles normes comptables selon chaque secteur marocain ?',/PCEC/],
 ['HPS active-t-il sa R&D en 2025 ?',/comptabilisés en charges/],
 ['IAS 38 autorise-t-elle les frais de recherche à l’actif ?',/dépenses de recherche sont des charges/],
 ['Quelles méthodes comptables ADI en 2025 ?',/méthode de l’achèvement/],
 ['PCSI RDS 2025 et comparatif 2024',/rétrospectivement/],
 ['IFRS 17 Wafa Assurance en 2025',/IFRS 4 et IAS 39/],
 ['IFRS 17 obligatoire pour AtlantaSanad en 2025 ?',/référentiel comptable en vigueur au Maroc/],
 ['Aradei IAS 40 en 2025 et ses immeubles en construction',/coût jusqu’à achèvement/],
 ['Normes comptables TGCC 2025',/avis n°5/],
 ['EQD en IFRS 9 automatiquement ?',/ne pas importer les stages IFRS 9/],
 ['Quel référentiel comptable pour Salafin ?',/PCEC/],
 ['Hausse des ECL stage 2 : la banque prévoit une crise au Maroc selon IFRS 9 ?',/ne prouve pas à elle seule/],
 ['Le dividende dépend-il du résultat consolidé ?',/ne détermine pas mécaniquement/],
 ['Explique IFRS 16 crédit-bail bailleur et preneur',/Distinguer bailleur et preneur/],
 ['Comment IAS 2 évalue les stocks ?',/plus faible du coût/],
 ['IAS 37 provisions pour contrats déficitaires',/obligation actuelle/],
 ['Normes comptables du courtier AFM et commissions',/pas traité comme un assureur/],
 ['Pourquoi le bénéfice HPS a baissé ?',/ne démontre pas à elle seule la cause/],
 ['Quel PER OCP ?',/absence de cotation en actions n’implique pas/],
 ['Normes comptables ONEE',/référentiel de 80 actions/],
];
let checked=0;
for(const [question,pattern] of cases){
 const r=api.localAnswer(question,data,'MASI');assert.equal(r.domain,'accounting',question);
 assert.match(r.text,pattern,question+'\n'+r.text);assert(r.sources.length,question);checked++;
}
for(const [symbol,row] of Object.entries(data.symbols)){
 const r=api.localAnswer('Quelles normes comptables '+symbol+' ?',data,'MASI');
 assert.equal(r.domain,'accounting');assert(r.text.includes(symbol));
 if(row.accounting_profile?.declared_basis)assert(r.text.includes(row.accounting_profile.declared_basis));
 checked++;
}
const old=api.localAnswer('Méthodes comptables HPS en 2024',data,'MASI');
assert(old.text.includes('pas de revue primaire distincte pour 2024'));
assert(!old.text.includes('143,7 MMAD'));
const semester=api.localAnswer('Normes comptables ADI S1 2026',data,'MASI');
assert(semester.text.includes('Les méthodes annuelles ne sont pas automatiquement reportées'));
assert(!semester.text.includes('simulation à règles 2024 constantes'));
let r=api.localAnswer('Normes comptables HPS en 2025',data,'MASI');
r=api.localAnswer('Et pour RDS ?',data,'HPS',r.context);
assert.equal(r.domain,'accounting');assert(r.text.includes('RDS'));assert(!r.text.includes('143,7 MMAD'));
const actual=api.localAnswer('Normes comptables ADI 2025 et PER',data,'MASI');
assert(actual.text.includes('PER canonique : '+data.symbols.ADI.fundamental.pe.toLocaleString('fr-FR',{maximumFractionDigits:2})));
assert.equal(JSON.stringify(data),original);
console.log('Accounting assistant: '+(checked+5)+' sourced answers and period/follow-up/immutability regressions passed; no LLM call.');
