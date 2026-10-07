/* Stable adverse-state fixtures: live market concordance is not a prerequisite
 * for publishing a truthful answer. No provider or network calls. */
const assert=require('node:assert/strict'),fs=require('node:fs');
const api=require('../web/assistant.js');
const published=JSON.parse(fs.readFileSync('web/assistant-data.json','utf8'));
const fmt=x=>typeof x==='number'?x.toLocaleString('fr-FR',{maximumFractionDigits:2}):'indisponible';
const labels=['totaux concordants','écart constaté','couverture non confirmée'];
let checked=0;
for(const [status,label,observed,expected] of [
  ['matched',labels[0],68,68],
  ['discrepancy',labels[1],68,68],
  ['incomplete',labels[2],60,68],
  ['unavailable',labels[2],0,null],
  ['unknown',labels[2],0,null],
  [null,labels[2],0,null],
]){
  for(const turnover of [246400986.77,0]){
    const data=structuredClone(published);
    data.market={...data.market,asof:'2026-10-07',masi:{asof:'2026-10-07'},
      turnover_mad:turnover,shares:722191,transactions:null};
    data.market_volume_audit={status,asof:'2026-10-07',observed_lines:observed,
      expected_lines:expected,coverage_complete:status==='matched'||status==='discrepancy',
      cdg_turnover_mad:turnover,lines_turnover_mad:status==='discrepancy'?turnover+100:turnover,
      difference_mad:status==='discrepancy'?100:0};
    const before=structuredClone(data);
    const result=api.localAnswer('Quel volume global MASI ?',data,'MASI');
    const diagnostic=JSON.stringify({status,turnover})+'\n'+result.text;
    assert.ok(result.text.includes('Volume global : '+fmt(turnover)+' MAD'),diagnostic);
    assert.ok(result.text.includes('722\u202f191 titres échangés'),diagnostic);
    assert.ok(result.text.includes('titres échangés · indisponible.'),diagnostic);
    assert.ok(result.text.includes(label),diagnostic);
    for(const other of labels.filter(x=>x!==label))assert.ok(!result.text.includes(other),diagnostic);
    assert.ok(result.text.includes(`${observed} / ${expected??'—'} lignes`),diagnostic);
    assert.ok(result.text.includes('Les fiches anciennes sont exclues'),diagnostic);
    assert.deepEqual(result.symbols,['MASI']);
    assert.equal(result.mode,'local');
    assert.ok(result.sources.some(s=>s.url==='index.html'));
    assert.deepEqual(data,before,'Answer must preserve source amounts, dates and audit');
    checked++;
  }
}
const absent=structuredClone(published);
absent.market={asof:'2026-10-07',masi:{asof:'2026-10-07'}};
delete absent.market_volume_audit;
let result=api.localAnswer('Quel volume global MASI ?',absent,'MASI');
assert.ok(result.text.includes('Volume global : indisponible'));
assert.ok(!result.text.includes('Volume global : 0 MAD'));
assert.ok(result.text.includes('couverture non confirmée · — / — lignes'));
assert.ok(!result.text.includes('totaux concordants'));
checked++;
absent.market.turnover_mad=null;
absent.market_volume_audit={status:'unavailable',observed_lines:0,expected_lines:null};
result=api.localAnswer('Quel volume global MASI ?',absent,'MASI');
assert.ok(result.text.includes('Volume global : indisponible'));
assert.ok(!result.text.includes('Volume global : 0 MAD'));
assert.ok(result.text.includes('couverture non confirmée · 0 / — lignes'));
assert.ok(!result.text.includes('totaux concordants'));
checked++;
result=api.localAnswer('Volume global MASI le 01/01/2023',absent,'MASI');
assert.ok(result.text.includes('Le volume global à cette date n’est pas disponible'));
assert.ok(!result.text.includes('Volume global :'));
assert.ok(!result.text.includes('totaux concordants'));
checked++;
for(const asof of ['2026-10-06','2026-10-07']){
  const data=structuredClone(published);
  data.market.asof='2026-10-07';data.symbols.MRL.asof=asof;
  const before=structuredClone(data);
  result=api.localAnswer('PER MRL',data,'MASI');
  assert.equal(result.text.includes('différente de la dernière clôture du marché'),asof!=='2026-10-07');
  assert.deepEqual(data,before);
  checked++;
}
console.log(`Assistant volume: ${checked} stable concordant/discrepant/incomplete/unavailable fixtures, zero vs missing amounts, dated scope, source preservation and no false concordance passed.`);
