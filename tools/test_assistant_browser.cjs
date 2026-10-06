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
    console.log(`Browser QA: ${interactions} page/viewport journeys; laboratory help click, Enter, Space, Escape, close, focus, unchanged filters and no-JS at 3 widths; assistant checks passed; no LLM call.`);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
