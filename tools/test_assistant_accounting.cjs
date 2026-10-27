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
 ['Normes comptables BCP 2025',/trois stages/,'BCP'],
 ['Normes comptables BOA 2025',/test SPPI/,'BOA'],
 ['IFRS 17 BMCI en 2025 ?',/non applicable au contexte de la BMCI/,'BMC'],
 ['Normes comptables CDM 2025 et couverture',/conserver IAS 39/,'CDM'],
 ['Normes comptables CIH 2025',/depuis le 1er janvier 2022/,'CIH'],
 ['Normes comptables CFGB 2025',/ne pas disposer d’immeubles de placement/,'CFGB'],
 ['IFRS 17 Sanlam 2025',/PAA pour le décès et la non-vie/,'SAF'],
 ['Méthodes comptables AFMA 2025',/Les logiciels acquis/,'AFM'],
 ['Méthodes comptables Immorente 2025',/réévaluée annuellement/,'IMI'],
 ['Méthodes comptables Balima 2025',/reste au coût historique/,'BAL'],
];
let checked=0;
for(const [question,pattern,symbol] of cases){
 const r=api.localAnswer(question,data,'MASI');assert.equal(r.domain,'accounting',question);
 if(symbol)assert(r.symbols.includes(symbol),question+' selected wrong issuer');
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

assert.equal(api.validURL('comptabilite.html','../'),'../comptabilite.html');
assert.equal(api.validURL('titres/IMI.html#verifications','../'),'../titres/IMI.html#verifications');
assert.equal(api.validURL('titres/IMI.html#unknown','../'),null);
// Stale quotes may legitimately leave no market-valued ratios in a dated fixture.
const stale=structuredClone(data);
for(const row of Object.values(stale.symbols))row.fundamental.pe=null;
const empty=api.localAnswer('Les 5 PER les plus faibles en 2025',stale,'BAL');
assert(empty.text.includes('0 titre(s) correspondant(s) sur 80 ; 0 affiché(s).'));
assert(!empty.text.includes('PER annuel :'));

console.log('Accounting assistant: '+(checked+6)+' sourced answers and period/follow-up/immutability regressions passed; no LLM call.');
