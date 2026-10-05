// Exercise the actual served script with minimal DOM controls, no dependencies.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const controls={};
for(const id of ['news-search','news-tier','news-scope','news-category','news-count','news-reset']){
  controls['#'+id]={value:'',handlers:{},addEventListener(type,cb){this.handlers[type]=cb;}};
}
const rows=[
  {dataset:{search:'bce inflation',tier:'S1',scope:'INTL',category:'macro'}},
  {dataset:{search:'maroc économie',tier:'S2',scope:'MAROC',category:'economie'}},
  {dataset:{search:'résultats tgcc',tier:'S1',scope:'MAROC',category:'bvc'}}
];
vm.runInNewContext(fs.readFileSync('web/nour.js','utf8'),{document:{
  querySelector:id=>controls[id]||null,
  querySelectorAll:selector=>selector==='[data-news-row]'?rows:[]
}});
const set=(id,value,type='change')=>{controls['#'+id].value=value;controls['#'+id].handlers[type]();};
assert.equal(controls['#news-count'].textContent,'3 liens affichés');
set('news-scope','MAROC');assert.deepEqual(rows.map(r=>r.hidden),[true,false,false]);
set('news-tier','S1');assert.deepEqual(rows.map(r=>r.hidden),[true,true,false]);
set('news-category','macro');assert(rows.every(r=>r.hidden));
controls['#news-reset'].handlers.click();assert(rows.every(r=>!r.hidden));
set('news-search','ECONOMIE','input');assert.deepEqual(rows.map(r=>r.hidden),[true,false,true]);
controls['#news-reset'].handlers.click();
set('news-search','resultats','input');assert.deepEqual(rows.map(r=>r.hidden),[true,true,false]);
console.log('News filters: scope, category, source, accents, reset and counts verified');
