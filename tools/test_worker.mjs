// Runtime-unit verification, no deployed Worker or real provider is called.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {webcrypto} from 'node:crypto';
import worker,{NourQuota,sha256,loadIndex} from '../backend/worker.mjs';
import {retrieve,sources} from '../backend/context.mjs';
if(!globalThis.crypto)Object.defineProperty(globalThis,'crypto',{value:webcrypto});
const index=JSON.parse(fs.readFileSync('web/assistant-context.json','utf8'));
const original=JSON.stringify(index);
const summary=retrieve(index,['ADI'],'Synthèse complète : marché, technique, fondamentaux, risques et sources');
assert(summary.selected.ADI.fundamental.warnings.length);
assert.equal(summary.selected.ADI.fundamental.net_debt_strict_mmad,null);
assert(sources(summary).some(s=>s.url.endsWith('#page=22')));
assert.equal(JSON.stringify(index),original);
assert(!summary.macro,'fondamentaux must not accidentally route to taux');
assert.throws(()=>retrieve(index,['../private'],'question'));
assert.throws(()=>retrieve(index,[['ADI']],'question'));

// Persistent, transactional storage double; reconstructing the object retains it.
const records=new Map();let queue=Promise.resolve();
const storage={async get(k){return structuredClone(records.get(k));},async put(k,v){records.set(k,structuredClone(v));},
  transaction(fn){const result=queue.then(()=>fn(this));queue=result.catch(()=>{});return result;}};
const limits={MONTHLY_CALL_LIMIT:'4',USER_MONTHLY_CALL_LIMIT:'2',USER_MINUTE_CALL_LIMIT:'2'};
let quota=new NourQuota({storage},limits);
const reserve=user=>quota.fetch(new Request('https://quota/reserve',{method:'POST',body:JSON.stringify({user})}));
assert.equal((await reserve('u1')).status,200);
quota=new NourQuota({storage},limits);
const concurrent=await Promise.all([reserve('u1'),reserve('u1'),reserve('u1')]);
assert.equal(concurrent.filter(r=>r.ok).length,1,'per-user limit survives restart and concurrent reservations');
assert.equal((await reserve('u2')).status,200);
assert.equal((await reserve('u2')).status,200);
assert.equal((await reserve('u3')).status,429,'global monthly cap across users');

const secret='temporary-test-code-for-nour-only';
const auth={'Content-Type':'application/json','Origin':'https://abdmoutalib207-lang.github.io','Authorization':'Bearer '+secret};
const payload={question:'Explique le PER ADI',symbols:['ADI'],consent:true,snapshot_id:index.snapshot_id};
const request=(body=payload,headers=auth,method='POST',path='/api/assistant')=>new Request('https://worker.test'+path,{method,headers,...(method==='POST'?{body:typeof body==='string'?body:JSON.stringify(body)}:{})});
let providerCalls=0,quotaCalls=0;
const env={NOUR_AI_ENABLED:'true',NOUR_ACCESS_KEYS:JSON.stringify({[await sha256(secret)]:{id:'noure',enabled:true}}),
  AI:{async run(model,body){providerCalls++;assert.equal(model,'@cf/mistralai/mistral-small-3.1-24b-instruct');assert(!JSON.stringify(body).includes('client-invented'));assert(JSON.stringify(body).includes('exceptionnels'));return {response:'Explication de test'};}},
  NOUR_QUOTA:{idFromName:name=>name,get:()=>({async fetch(){quotaCalls++;return new Response('',{status:200});}})}};
const originalFetch=globalThis.fetch;
const indexFetch=async (url,options)=>{assert.equal(url,'https://abdmoutalib207-lang.github.io/bvc-analyzer-nour/assistant-context.json');assert.equal(options.redirect,'manual');assert.equal(options.headers.Accept,'application/json');assert.equal(options.headers.Authorization,undefined);return new Response(JSON.stringify(index));};
globalThis.fetch=indexFetch;
try{
  assert.equal((await worker.fetch(request(payload,{...auth,Origin:'https://evil.test'}),env)).status,403);
  assert.equal((await worker.fetch(request(payload,{...auth,Authorization:''}),env)).status,401);
  assert.equal((await worker.fetch(request(payload,{...auth,Authorization:'Bearer '+secret+'bad'}),env)).status,401);
  assert.equal((await worker.fetch(request(payload,auth,'POST','/other'),env)).status,404);
  assert.equal((await worker.fetch(request({...payload,consent:false}),env)).status,400);
  assert.equal((await worker.fetch(request({...payload,question:'x'.repeat(1201)}),env)).status,400);
  assert.equal((await worker.fetch(request('x'.repeat(8193)),env)).status,413);
  assert.equal((await worker.fetch(request({...payload,snapshot_id:'old'}),env)).status,409);
  assert.equal((await worker.fetch(request(),{...env,NOUR_AI_ENABLED:'false'})).status,503);
  assert.equal((await worker.fetch(request(),{...env,NOUR_AI_ENABLED:undefined})).status,503);
  assert.equal((await worker.fetch(request(),{...env,NOUR_QUOTA:null})).status,503);
  assert.equal(providerCalls,0);assert.equal(quotaCalls,0);
  const response=await worker.fetch(request({...payload,context:{price:'client-invented'},url:'https://evil.test'}),env);
  const answer=await response.json();assert.equal(response.status,200);assert.equal(answer.mode,'llm');
  assert.equal(answer.snapshot_id,index.snapshot_id);assert(answer.sources.some(s=>s.url.includes('#page=50')));
  assert.equal(response.headers.get('Access-Control-Allow-Origin'),auth.Origin);
  assert.equal(response.headers.get('Cache-Control'),'no-store');assert.equal(providerCalls,1);
  const rejected=await worker.fetch(request(),{...env,NOUR_QUOTA:{idFromName:n=>n,get:()=>({fetch:async()=>new Response('',{status:429})})}});
  assert.equal(rejected.status,429);assert.equal(providerCalls,1);
  const rotated={...env,NOUR_ACCESS_KEYS:JSON.stringify({[await sha256(secret)]:{id:'noure',enabled:false}})};
  assert.equal((await worker.fetch(request(),rotated)).status,401);
  assert.equal(providerCalls,1);
  const cors=await worker.fetch(request(null,auth,'OPTIONS'),env);assert.equal(cors.status,204);
  // Source failures expose only bounded diagnostics and never consume AI quota.
  const counts=[providerCalls,quotaCalls];
  for(const [fetcher,diagnostic] of [
    [async()=>new Response('',{status:302,headers:{Location:'https://evil.test'}}),'http_302'],
    [async()=>new Response('',{status:403}),'http_403'],
    [async()=>{throw new TypeError('private upstream detail');},'fetch_TypeError'],
    [async()=>new Response('not json'),'invalid_json'],
    [async()=>new Response(JSON.stringify({...index,schema_version:'wrong'})),'invalid_schema'],
    [async()=>new Response('x'.repeat(2000001)),'too_large']
  ]){
    globalThis.fetch=fetcher;
    const failure=await worker.fetch(request(),env);assert.equal(failure.status,503);
    const message=(await failure.json()).error;assert(message.includes(diagnostic));assert(!message.includes('private upstream detail'));
    assert.deepEqual([providerCalls,quotaCalls],counts);
  }
  globalThis.fetch=indexFetch;
  assert.equal((await loadIndex()).snapshot_id,index.snapshot_id);
}finally{globalThis.fetch=originalFetch;}
console.log('Worker unit checks: compact retrieval, cited pages, immutable facts, consent, origin, code rotation, kill switch, persistent transactional quotas, snapshot drift and provider isolation passed. Cloudflare deployment/live inference not measured.');
