/* Real browser verification; only static pages and local deterministic answers.
 * Optional argument is an explicitly chosen Nour URL. Never calls a provider.
 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.argv[2]||'http://127.0.0.1:8766/';
const shots=process.env.NOUR_SCREENSHOTS;
(async()=>{
  const browser=await chromium.launch({headless:true});
  let interactions=0;
  try{
    for(const width of [375,768,1440]){
      const context=await browser.newContext({viewport:{width,height:900}});
      const errors=[];const page=await context.newPage();
      page.on('pageerror',error=>errors.push(error.message));
      page.on('response',response=>{if(response.status()>=400)errors.push(response.status()+' '+response.url());});
      for(const route of ['index.html','titres/JET.html','recherche.html','macro.html']){
        await page.goto(new URL(route,base).href,{waitUntil:'networkidle'});
        if(route==='recherche.html'){
          await page.locator('#lab-symbol').selectOption('ADI');
          const metrics=await page.locator('#lab-metrics').innerText();
          const help=page.locator('#lab-help');
          const toggle=page.locator('#lab-help-toggle');
          assert.equal(await help.evaluate(el=>el.open),false);
          await toggle.click();
          assert.equal(await page.locator('#lab-help-content').isVisible(),true);
          assert.ok((await page.locator('#lab-help-content').innerText()).includes('Cela ne prédit pas demain'));
          const helpRect=await page.locator('#lab-help-content').boundingBox();
          assert.ok(helpRect.x>=0&&helpRect.x+helpRect.width<=width+1);
          const touch=await toggle.boundingBox();
          assert.ok(touch.width>=44&&touch.height>=44);
          if(shots){
            fs.mkdirSync(shots,{recursive:true});
            await page.screenshot({path:path.join(shots,`lab-help-${width}.png`)});
          }
          await page.locator('#lab-help-close').click();
          assert.equal(await help.evaluate(el=>el.open),false);
          assert.equal(await toggle.evaluate(el=>el===document.activeElement),true);
          await page.keyboard.press('Enter');
          assert.equal(await help.evaluate(el=>el.open),true);
          await page.keyboard.press('Escape');
          assert.equal(await help.evaluate(el=>el.open),false);
          await page.keyboard.press('Space');
          assert.equal(await help.evaluate(el=>el.open),true);
          await toggle.click();
          assert.equal(await help.evaluate(el=>el.open),false);
          assert.equal(await page.locator('#lab-symbol').inputValue(),'ADI');
          assert.equal(await page.locator('#lab-metrics').innerText(),metrics);
        }
        await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
        await page.getByText('Données chargées · analyse du',{exact:false}).waitFor();
        assert.equal(await page.locator('#assistant-symbol option').count(),81);
        assert.equal(await page.locator('#assistant-ai-option').isVisible(),false);
        const expected=route.startsWith('titres/')?'JET':'MASI';
        assert.equal(await page.locator('#assistant-symbol').inputValue(),expected);
        await page.locator('#assistant-symbol').selectOption('JET');
        await page.locator('[data-assistant-question="Quels fondamentaux sont disponibles ?"]').click();
        await page.getByText('PER :',{exact:false}).last().waitFor();
        const report=await (await context.request.get(new URL('report.json',base).href)).json();
        const jet=report.results.find(row=>row.symbol==='JET');
        const messages=await page.locator('#assistant-messages').innerText();
        assert.ok(messages.includes(jet.fundamental.pe.toLocaleString('fr-FR',{maximumFractionDigits:2})));
        assert.ok(messages.includes('2026-06-30'));
        assert.ok(messages.includes('Réserves à lire'));
        assert.ok(messages.includes(jet.fundamental.latest_report.note));
        assert.ok(!messages.includes('selected_pages_reconciled_'));
        const docLink=page.locator('.assistant-sources a').filter({hasText:'JET · comptes annuels'});
        assert.equal(await docLink.getAttribute('href'),jet.fundamental.document_url);
        // The current session may legitimately be incomplete or discrepant.
        // Check the actual exported state, never assume every daily run matches.
        const exportFacts=await (await context.request.get(new URL('assistant-data.json',base).href)).json();
        await page.locator('#assistant-question').fill('Quel volume global MASI ?');
        await page.getByRole('button',{name:'Envoyer',exact:true}).click();
        await page.locator('#assistant-send:not([disabled])').waitFor();
        const volumeAnswer=await page.locator('.assistant-message[data-role="assistant"]').last().innerText();
        const amount=exportFacts.market.turnover_mad;
        assert.ok(volumeAnswer.includes('Volume global : '+(amount===null||amount===undefined?'indisponible':amount.toLocaleString('fr-FR',{maximumFractionDigits:2})+' MAD')));
        const volumeState=exportFacts.market_volume_audit?.status;
        const volumeLabel=volumeState==='matched'?'totaux concordants':volumeState==='discrepancy'?'écart constaté':'couverture non confirmée';
        assert.ok(volumeAnswer.includes(volumeLabel),volumeAnswer);
        assert.equal(volumeAnswer.includes('totaux concordants'),volumeState==='matched');
        await page.locator('#assistant-question').fill('MM50 ADI');
        await page.getByRole('button',{name:'Envoyer',exact:true}).click();
        const adi=report.results.find(row=>row.symbol==='ADI');
        await page.getByText('MM50 : '+adi.technical.sma50.toLocaleString('fr-FR',{maximumFractionDigits:2}),{exact:false}).last().waitFor();
        assert.equal(await page.locator('#assistant-symbol').inputValue(),'ADI');
        await page.locator('#assistant-question').fill('Et son RSI ?');
        await page.getByRole('button',{name:'Envoyer',exact:true}).click();
        await page.getByText('RSI 14 : '+adi.technical.rsi14.toLocaleString('fr-FR',{maximumFractionDigits:2}),{exact:false}).last().waitFor();
        const last=await page.locator('.assistant-message[data-role="assistant"]').last().innerText();
        assert.ok(last.includes('ADI · Alliances'));
        assert.ok(!last.includes('PER :'));
        if(route==='recherche.html'){
          async function ask(question){
            await page.locator('#assistant-question').fill(question);
            await page.getByRole('button',{name:'Envoyer',exact:true}).click();
            await page.locator('#assistant-send:not([disabled])').waitFor();
            return page.locator('.assistant-message[data-role="assistant"]').last().innerText();
          }
          const menu=await ask('Quelles fonctions peux-tu expliquer ?');
          const facts=await (await context.request.get(new URL('assistant-data.json',base).href)).json();
          for(const c of facts.knowledge.capabilities)assert.ok(menu.includes(c.label));
          const risk=await ask('Quels risques pour ADI face au MASI ?');
          assert.ok(risk.includes('Bêta : '+adi.market_risk.beta.toLocaleString('fr-FR',{maximumFractionDigits:2})));
          assert.equal(await page.locator('#assistant-symbol').inputValue(),'ADI');
          const definition=await ask('Que veut dire bêta ?');
          assert.ok(definition.includes(facts.knowledge.definitions.beta));
          assert.ok(definition.includes('ADI · Alliances'));
          await ask('Compare le PER d’ADI et RDS');
          const comparison=await ask('Et leur BPA ?');
          for(const s of ['ADI','RDS']){
            assert.ok(comparison.includes(s+' ·'));
            const eps=facts.symbols[s].fundamental.eps_mad;
            assert.ok(comparison.includes('BPA : '+(eps===null?'indisponible':eps.toLocaleString('fr-FR',{maximumFractionDigits:2}))));
          }
          await ask('Quel est le RNPG de JET au premier semestre 2026 ?');
          const total=await ask('Et le résultat total ?');
          assert.ok(total.includes('Résultat net consolidé total : '+jet.fundamental.latest_report.reported_total_net_millions.toLocaleString('fr-FR',{maximumFractionDigits:2})));
          assert.ok(total.includes('période 2026-06-30'));
          const helpAnswer=await ask('À quoi sert le laboratoire ?');
          assert.ok(helpAnswer.includes(facts.knowledge.definitions.laboratory));
          assert.ok(!helpAnswer.includes('médiane nette'));
          await page.locator('#assistant-symbol').selectOption('ADI');
          const brief=await ask('Résume le briefing de clôture');
          for(const paragraph of facts.briefings.cloture.editorial.paragraphs)assert.ok(brief.includes(paragraph));
          const lab=await ask('Laboratoire ADI sur 20 séances achat 1 %, vente 1 %');
          const expectedLab=await page.evaluate(()=>{
            const data=JSON.parse(document.getElementById('lab-data').textContent);
            return NourResearch.summary(NourResearch.select(data.rows,{symbol:'ADI',horizon:20,period:'all',regime:'all'}),1,1,0);
          });
          assert.ok(lab.includes(expectedLab.count+' observations'));
          assert.ok(lab.includes('médiane nette '+expectedLab.median.toLocaleString('fr-FR',{maximumFractionDigits:2})));
          const follow=await ask('Et sur 60 séances avec glissement 0,2 % ?');
          assert.ok(follow.includes('ADI · laboratoire 60 séances'));
          assert.ok(follow.includes('achat 1 %, vente 1 %, glissement 0,2 %'));
          const csv=await (await context.request.get(new URL('historique/ADI.csv',base).href)).text();
          const first=csv.split(/\r?\n/)[1].split(';');
          const old=await ask('Bougie ADI le '+first[0]);
          assert.ok(old.includes('Clôture du '+first[0]+' : '+Number(first[5]).toLocaleString('fr-FR',{maximumFractionDigits:2})));
          assert.ok(old.includes('Ouverture '+Number(first[2]).toLocaleString('fr-FR',{maximumFractionDigits:2})));
          assert.ok(await page.locator('.assistant-message').last().locator('a[href$="historique/ADI.csv"]').count()===1);
          const oldVolume=await ask('Et le volume ?');
          assert.ok(oldVolume.includes('Quantité échangée du '+first[0]+' : '+Number(first[6]).toLocaleString('fr-FR',{maximumFractionDigits:2})));
          assert.ok(!oldVolume.includes('Volume de la dernière séance'));
          await page.locator('#assistant-symbol').selectOption('JET');
          const reset=await ask('Et son BPA ?');
          assert.ok(reset.includes('JET · Jet Contractors'));
          assert.ok(!reset.includes('Clôture du '+first[0]));
          assert.ok(!reset.includes('ADI · Alliances'));
        }
        const rect=await page.locator('#assistant-dialog').boundingBox();
        assert.ok(rect.x>=0&&rect.y>=0&&rect.x+rect.width<=width+1&&rect.y+rect.height<=901);
        await page.getByRole('button',{name:'Effacer',exact:true}).click();
        assert.equal(await page.locator('.assistant-message').count(),0);
        await page.locator('#assistant-question').fill('<img src=x onerror=alert(1)> MASI le 31/03/26');
        await page.getByRole('button',{name:'Envoyer',exact:true}).click();
        await page.getByText('Clôture du 2026-03-31 :',{exact:false}).waitFor();
        assert.equal(await page.locator('#assistant-messages img').count(),0);
        assert.equal(await page.locator('#assistant-ai').isChecked(),false);
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#assistant-dialog').isVisible(),false);
        assert.equal(await page.locator('#assistant-open').evaluate(el=>el===document.activeElement),true);
        interactions++;
      }
      if(shots){
        await page.goto(new URL('titres/JET.html',base).href,{waitUntil:'networkidle'});
        await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
        await page.getByText('Données chargées · analyse du',{exact:false}).waitFor();
        await page.locator('[data-assistant-question="Quels fondamentaux sont disponibles ?"]').click();
        await page.getByText('PER :',{exact:false}).last().waitFor();
        fs.mkdirSync(shots,{recursive:true});
        await page.screenshot({path:path.join(shots,`assistant-${width}.png`)});
      }
      assert.deepEqual(errors,[],'Browser/page/network errors');
      await context.close();
      const nojs=await browser.newContext({viewport:{width,height:900},javaScriptEnabled:false});
      const native=await nojs.newPage();
      await native.goto(new URL('recherche.html',base).href);
      await native.locator('#lab-help-toggle').click();
      assert.equal(await native.locator('#lab-help-content').isVisible(),true);
      assert.equal(await native.locator('#lab-help-close').isVisible(),false);
      await native.locator('#lab-help-toggle').click();
      assert.equal(await native.locator('#lab-help-content').isVisible(),false);
      await nojs.close();
    }
    console.log(`Browser QA: ${interactions} page/viewport journeys; natural definitions, comparison and semester follow-ups, benchmark MASI subject, global briefing, lab parity, cost/horizon follow-up, full CSV date/volume follow-up and explicit context reset; laboratory help and no-JS at 3 widths; no LLM call.`);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
