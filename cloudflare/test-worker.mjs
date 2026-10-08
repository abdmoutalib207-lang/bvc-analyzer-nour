import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
if(!globalThis.crypto) Object.defineProperty(globalThis,'crypto',{value:webcrypto});
const source=fs.readFileSync(new URL('./worker.js',import.meta.url),'utf8');
const real=JSON.parse(fs.readFileSync(new URL('../web/assistant-data.json',import.meta.url),'utf8'));
const nativeFetch=globalThis.fetch, base='https://bvc-nour-assistant.abdmoutalib207.workers.dev';
const token='fixture-only-private-access-code';
let moduleId=0, checks=0;
async function setup({snapshot=real,result={response:'Réponse de test'},error=false}={}) {
  const worker=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')+'#'+moduleId++)).default;
  let calls=0, reads=0, prompt;
  globalThis.fetch=async (url,options)=>{reads++;assert.equal(url,'https://abdmoutalib207-lang.github.io/bvc-analyzer-nour/assistant-data.json');assert.equal(options.redirect,'error');return Response.json(snapshot);};
  const env={NOUR_ACCESS_TOKEN:token,AI:{run:async (model,args)=>{calls++;assert.equal(model,'@cf/mistralai/mistral-small-3.1-24b-instruct');assert.equal(args.max_tokens,700);assert.equal(args.stream,false);prompt=JSON.parse(args.messages[1].content);if(error)throw Error('provider-private-detail');return result;}}};
  const request=(payload={question:'PER ADI',symbols:['ADI'],consent:true},options={})=>{
    const headers={'Origin':'https://abdmoutalib207-lang.github.io','Authorization':'Bearer '+token,'Content-Type':'application/json',...options.headers};
    return new Request(base+(options.path||'/api/assistant'),{method:options.method||'POST',headers,...(options.method==='GET'||options.method==='OPTIONS'?{}:{body:options.body??JSON.stringify(payload)})});
  };
  return {worker,env,request,calls:()=>calls,reads:()=>reads,prompt:()=>prompt};
}
async function expect(s,status,payload,options) {const r=await s.worker.fetch(s.request(payload,options),s.env);assert.equal(r.status,status,await r.clone().text());checks++;return r;}
try {
  let s=await setup();
  const page=await s.worker.fetch(new Request(base),s.env);assert.equal(page.status,200);
  assert.match(page.headers.get('content-security-policy'),/script-src 'nonce-/);
  const html=await page.text();assert.ok(!html.includes(token));assert.ok(!html.includes('localStorage'));assert.match(html,/textContent=d.text/);
  new vm.Script(html.match(/<script nonce="[^"]+">([\s\S]+)<\/script>/)[1]); checks++;
  const status=await s.worker.fetch(new Request(base+'/api/assistant/status'),s.env);assert.equal((await status.json()).configured,true);assert.equal(s.calls(),0);checks++;
  await expect(s,204,undefined,{method:'OPTIONS'});assert.equal(s.calls(),0);
  await expect(s,403,undefined,{headers:{Origin:'https://evil.example'}});
  await expect(s,403,undefined,{headers:{Origin:''}});
  await expect(s,401,undefined,{headers:{Authorization:''}});
  await expect(s,401,undefined,{headers:{Authorization:'Bearer incorrect'}});
  await expect(s,415,undefined,{headers:{'Content-Type':'text/plain'}});
  await expect(s,400,undefined,{body:'{'});
  await expect(s,413,undefined,{body:'x'.repeat(8193)});
  await expect(s,403,{question:'PER ADI',symbols:['ADI'],consent:false});
  await expect(s,400,{question:' ',symbols:['ADI'],consent:true});
  await expect(s,400,{question:'x'.repeat(1201),symbols:['ADI'],consent:true});
  await expect(s,400,{question:'PER ADI',symbols:['ADI'],consent:true,facts:{price:999}});
  await expect(s,400,{question:'PER ADI',symbols:['__proto__'],consent:true});
  await expect(s,400,{question:'PER ADI',symbols:['ZZZZ'],consent:true});
  await expect(s,400,{question:'PER ADI',symbols:[],consent:true});
  await expect(s,400,{question:'Compare ADI RDS JET',symbols:['ADI'],consent:true});
  await expect(s,400,{question:'MASI 2026-02-30',symbols:['MASI'],consent:true});
  assert.equal(s.calls(),0);
  const good=await expect(s,200);const body=await good.json();assert.equal(body.mode,'llm');assert.equal(body.analysis_date,real.analysis_date);
  assert.equal(s.prompt().releve_nour.selected.ADI.fundamental.pe,real.symbols.ADI.fundamental.pe);
  assert.deepEqual(s.prompt().releve_nour.selected.ADI.fundamental.latest_report,real.symbols.ADI.fundamental.latest_report);
  assert.equal(body.sources[1].url,base.replace('bvc-nour-assistant.abdmoutalib207.workers.dev','abdmoutalib207-lang.github.io/bvc-analyzer-nour')+'/titres/ADI.html');
  assert.equal(good.headers.get('access-control-allow-origin'),'https://abdmoutalib207-lang.github.io');
  const masi=await expect(s,200,{question:'Volume global MASI',symbols:['MASI'],consent:true});
  assert.deepEqual(s.prompt().releve_nour.selected.MASI.volume_audit,real.market_volume_audit);
  assert.equal(s.prompt().releve_nour.selected.MASI.market.turnover_mad,real.market.turnover_mad);
  await expect(s,200,{question:'Quels risques pour ADI ?',symbols:['MASI'],consent:true});assert.ok(s.prompt().releve_nour.selected.ADI);
  await expect(s,200,{question:'A quoi sert le laboratoire ?',symbols:['MASI'],consent:true});assert.ok(s.prompt().releve_nour.laboratory.notice.includes('non recalculés'));
  await expect(s,429);assert.equal(s.calls(),4);
  for(const result of [{choices:[{message:{content:'Compatibilité'}}]},{response:''},{response:123},{response:'x'.repeat(10001)}]) {
    s=await setup({result});await expect(s,typeof result.choices!=='undefined'?200:502);
  }
  s=await setup({error:true});const failure=await expect(s,503);assert.ok(!(await failure.text()).includes('provider-private-detail'));
  s=await setup();delete s.env.AI;await expect(s,503);assert.equal(s.calls(),0);
  s=await setup();s.env.NOUR_ACCESS_TOKEN='short';await expect(s,503);assert.equal(s.calls(),0);
  for(const snapshot of [{...real,schema_version:'wrong'},{...real,analysis_date:'2099-01-01'},{...real,analysis_date:'2026-02-30'}]) {
    s=await setup({snapshot});await expect(s,503);assert.equal(s.calls(),0);
  }
  const future=structuredClone(real);future.symbols.ADI.asof='2099-01-01';s=await setup({snapshot:future});await expect(s,503);assert.equal(s.calls(),0);
  s=await setup();globalThis.fetch=async()=>new Response('upstream secret detail',{status:500});const noSource=await expect(s,503);assert.equal(s.calls(),0);assert.ok(!(await noSource.text()).includes('secret detail'));
  s=await setup();let release;const latch=new Promise(resolve=>release=resolve);s.env.AI.run=async()=>{await latch;return {response:'Réponse'};};
  const p1=s.worker.fetch(s.request(),s.env),p2=s.worker.fetch(s.request(),s.env);
  // Give asynchronous auth/source validation time to reserve both slots.
  await new Promise(resolve=>setTimeout(resolve,25));await expect(s,429);release();assert.equal((await p1).status,200);assert.equal((await p2).status,200);
  console.log(`Cloudflare Worker: ${checks} input/auth/source/quota/response checks passed. AI mocked; no real inference or account changes.`);
} finally {globalThis.fetch=nativeFetch;}
