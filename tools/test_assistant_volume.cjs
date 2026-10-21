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
assert.ok(result.text.includes('Le volume global au 2023-01-01 n’est pas disponible'));
assert.ok(!result.text.includes('Volume global :'));
assert.ok(!result.text.includes('totaux concordants'));
checked++;
for(const asof of ['2026-10-06','2026-10-07']){
  const data=structuredClone(published);
  data.market={...data.market,status:'closed',asof:'2026-10-07',masi:{...data.market.masi,asof:'2026-10-07'}};data.symbols.MRL.asof=asof;
  const before=structuredClone(data);
  result=api.localAnswer('PER MRL',data,'MASI');
  assert.equal(result.text.includes('différente de la dernière clôture du marché'),asof!=='2026-10-07');
  assert.deepEqual(data,before);
  checked++;
}
for(const verified of [true,false]){
  const data=structuredClone(published);
  data.cross_source_volume_audit={status:verified?'matched':'unavailable',session:data.market.asof,
    observed_at:'2026-10-18T21:00:00Z',cross_source_verified:verified,quantities_cross_source_verified:verified};
  result=api.localAnswer('Quel volume global MASI ?',data,'MASI');
  assert.equal(result.text.includes('montants confirmés'),verified);
  assert.equal(result.text.includes('Recoupement externe non confirmé : unavailable'),!verified);
  checked++;
}
for(const shares of [undefined,null,0,1]){
  const data=structuredClone(published);
  data.market={asof:'2026-10-19',status:'intraday',turnover_mad:0,shares,transactions:103};
  data.market_volume_audit={status:'incomplete',observed_lines:0,expected_lines:0};
  data.cross_source_volume_audit={status:'intraday',cross_source_verified:false};
  const before=structuredClone(data);
  result=api.localAnswer('Quel volume global MASI ?',data,'MASI');
  assert.ok(result.text.includes('Volume global : 0 MAD'));
  assert.ok(result.text.includes('103 transactions'));
  assert.ok(result.text.includes(shares==null?'titres échangés : indisponible':shares+' titres échangés'));
  assert.ok(!result.text.includes('totaux concordants'));
  assert.ok(!result.text.includes('montants confirmés'));
  assert.deepEqual(data,before);
  checked++;
}
{
  const data=structuredClone(published);
  data.market={asof:'2026-10-19',status:'closed',turnover_mad:544.03,shares:41};
  data.market_volume_audit={status:'incomplete',observed_lines:2,expected_lines:3};
  data.cross_source_volume_audit={status:'detail_matched',publication_scope:'validated_title_lines',cross_source_verified:true,
    quantities_cross_source_verified:true,totals:{retained_after:{quoted:2,turnover_mad:'500.03',shares:30}}};
  const before=structuredClone(data),answer=api.localAnswer('Quel volume global MASI ?',data,'MASI');
  assert.ok(answer.text.includes('Volume global : 544,03 MAD'));
  assert.ok(answer.text.includes('Total global annoncé non confirmé'));
  assert.ok(answer.text.includes('500,03 MAD'));
  assert.ok(!answer.text.includes('totaux concordants'));
  assert.ok(!answer.text.includes('montants confirmés'));
  assert.deepEqual(data,before);checked++;
}
{
  const data=structuredClone(published);
  data.market={asof:'2026-10-19',status:'closed',turnover_mad:113956983.12,shares:876356,transactions:null,
    transactions_reported:2851,transactions_quality:{status:'session_not_independently_attested'},
    official_reference:{asof:'2026-10-19',contracts:3671,turnover_mad:'113956983.12',shares:876356,review_status:'manual_capture_reviewed',source_url:'https://www.casablanca-bourse.com/market-data/volume'}};
  // This scenario has 61 detailed lines for 62 announced lines. Do not inherit
  // a live audit that may legitimately become matched on a later session.
  data.market_volume_audit={status:'incomplete',asof:'2026-10-19',observed_lines:61,expected_lines:62,
    coverage_complete:false,cdg_turnover_mad:113956983.12,lines_turnover_mad:113956939.12,
    difference_mad:-44,cdg_shares:876356,lines_shares:876345,difference_shares:-11};
  data.cross_source_volume_audit={publication_scope:'validated_title_lines',totals:{retained_after:{quoted:61,turnover_mad:'113956939.12',shares:876345}}};
  const before=structuredClone(data);
  for(const question of ['Quel volume global MASI ?','Combien de transactions MASI ?','Combien de contrats MASI ?']){
    const answer=api.localAnswer(question,data,'MASI');
    assert.ok(answer.text.includes('3\u202f671 contrats'),answer.text);
    assert.ok(!answer.text.includes('2\u202f851 transactions'),answer.text);
    assert.ok(answer.text.includes('date propre non attestée'),answer.text);
    assert.ok(answer.text.includes('capture fournie par l’utilisateur et revue manuellement'),answer.text);
    if(question.includes('volume')){
      assert.ok(answer.text.includes('Total global corroboré'),answer.text);
      assert.ok(answer.text.includes('décomposition à rapprocher'),answer.text);
    }
    assert.ok(!answer.text.includes('totaux concordants'),answer.text);checked++;
  }
  assert.deepEqual(data,before);
  const old=api.localAnswer('Combien de contrats MASI le 16/10/2026 ?',data,'MASI');
  assert.ok(!old.text.includes('3\u202f671 contrats'),old.text);
  const moved=structuredClone(data);moved.market.asof='2026-10-20';
  assert.ok(!api.localAnswer('Combien de contrats MASI ?',moved,'MASI').text.includes('3\u202f671 contrats'));
}
{
  const data=structuredClone(published);
  data.volume_history=JSON.parse(fs.readFileSync('data/volume_history.json','utf8'));
  const before=structuredClone(data);
  const old=api.localAnswer('Combien de transactions MASI le 16/10/2026 ?',data,'MASI');
  assert.ok(old.text.includes('3\u202f114 transactions'),old.text);
  assert.ok(old.text.includes('Marché central'),old.text);
  assert.ok(!old.text.includes('3\u202f671 transactions'),old.text);
  assert.ok(old.sources.some(s=>s.url==='historique-volumes.html'));
  const oct12=api.localAnswer('Quel volume global MASI le 12/10/2026 ?',data,'MASI');
  assert.ok(oct12.text.includes('52\u202f945\u202f136,05 MAD'),oct12.text);
  assert.ok(oct12.text.includes('199\u202f770 titres échangés'),oct12.text);
  const absent=api.localAnswer('Quel volume global MASI le 18/09/2026 ?',data,'MASI');
  assert.ok(absent.text.includes('n’est pas disponible'),absent.text);
  assert.ok(!absent.text.includes('Export historique daté'),absent.text);
  assert.deepEqual(data,before);checked+=3;
}
console.log(`Assistant volume: ${checked} stable concordant/discrepant/incomplete/unavailable fixtures, zero vs missing amounts, dated scope, source preservation and no false concordance passed.`);
