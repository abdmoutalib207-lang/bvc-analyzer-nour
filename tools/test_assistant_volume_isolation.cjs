/* Run the complete volume fixtures against changing live audit states. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const vm=require('node:vm'),{createRequire}=require('node:module');
const filename=path.join(__dirname,'test_assistant_volume.cjs');
const source=fs.readFileSync(filename,'utf8'),realRequire=createRequire(filename);
const snapshot=JSON.parse(fs.readFileSync(path.join(__dirname,'../web/assistant-data.json'),'utf8'));
let checked=0;
for(const status of ['matched','discrepancy','incomplete','unavailable']){
  const data=structuredClone(snapshot);
  data.market_volume_audit={status,asof:data.market?.asof,observed_lines:62,expected_lines:62,
    coverage_complete:status==='matched'||status==='discrepancy'};
  const before=structuredClone(data);
  const scopedFS={...fs,readFileSync(file,...args){
    return file==='web/assistant-data.json'?JSON.stringify(data):fs.readFileSync(file,...args);
  }};
  const run=vm.runInThisContext('(function(require,structuredClone,console){\n'+source+'\n})',{filename});
  run(name=>name==='node:fs'?scopedFS:realRequire(name),structuredClone,{log(){}});
  assert.deepEqual(data,before,'Fixture suite mutated the source snapshot');checked++;
}
console.log(`Assistant volume isolation: complete suite passed with ${checked} different live audit states; source snapshot preserved.`);
