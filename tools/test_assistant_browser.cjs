/* Real browser verification; only static pages and local deterministic answers.
 * Optional argument is an explicitly chosen Nour URL. Never calls a provider.
 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.argv[2]||'http://127.0.0.1:8766/';
const shots=process.env.NOUR_SCREENSHOTS;
// An absent canonical number must be visibly absent, never coerced to zero.
const answerNumber=value=>Number.isFinite(value)?value.toLocaleString('fr-FR',{maximumFractionDigits:2}):'indisponible';
async function assertQuote(locator,value){
  const expected=Number.isFinite(value)?value.toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
  assert.equal((await locator.innerText()).replace(/\s/g,''),expected.replace(/\s/g,'')+'MAD');
}
(async()=>{
  const browser=await chromium.launch({headless:true});
  let interactions=0;const assetAnomalies=[];
  try{
    for(const width of [375,768,1440]){
      const context=await browser.newContext({viewport:{width,height:900}});
      // The loopback server deliberately exposes only its local LLM gateway.
      // Browser QA for static Pages must instead load the exact public config.
      await context.route('**/assistant-config.json',async request=>{
        await request.fulfill({status:200,contentType:'application/json',
          body:fs.readFileSync(path.join(__dirname,'../web/assistant-config.json'),'utf8')});
      });
      const errors=[];const page=await context.newPage();let marketReport;
      page.on('pageerror',error=>errors.push(error.message));
      page.on('response',response=>{if(response.status()>=400){if(/\/logos\/[A-Z0-9]+\.svg(?:\?|$)/.test(response.url()))assetAnomalies.push({url:response.url(),http_status:response.status(),severity:'warning',at:new Date().toISOString()});else errors.push(response.status()+' '+response.url());}});
      for(const route of ['index.html','titres/JET.html','titres/ADI.html','titres/MNG.html','titres/MUT.html','titres/ENK.html','titres/CFGB.html','recherche.html','metiers.html','sources.html','macro.html','anomalies.html']){
        await page.goto(new URL(route,base).href,{waitUntil:'networkidle'});
        if(route==='index.html'){
          assert.equal(await page.locator('[data-market-row] .company-logo').count(),80);
          await page.locator('[data-market-row] .company-logo img').evaluateAll(images=>images.forEach(img=>img.loading='eager'));
          await page.waitForFunction(()=>[...document.querySelectorAll('[data-market-row] .company-logo img')].every(img=>img.complete));
          const failedLogos=await page.locator('[data-market-row] .company-logo img').evaluateAll(images=>images.filter(img=>img.naturalWidth===0).map(img=>({src:img.currentSrc||img.src,complete:img.complete})));
          if(failedLogos.length){
            await page.locator('[data-market-row] .company-logo img').evaluateAll(async images=>{
              await Promise.all(images.filter(img=>!img.naturalWidth).map(async img=>{
                const retry=new URL(img.src);retry.searchParams.set('nour_qa_retry','1');img.src=retry.href;
                try{await img.decode();img.closest('.company-logo').classList.remove('is-missing');}catch{}
              }));
            });
            const fallback=await page.locator('[data-market-row] .company-logo img').evaluateAll(images=>images.filter(img=>!img.naturalWidth).map(img=>({src:img.src,
              degraded:img.closest('.company-logo').classList.contains('is-missing'),
              readable:img.closest('.company-logo').innerText.trim().length>0})));
            for(const x of fallback)assert.ok(x.degraded&&x.readable,'Logo failure without visible ticker fallback: '+x.src);
            assetAnomalies.push(...failedLogos.map(x=>({...x,severity:'warning',at:new Date().toISOString(),fallback_verified:true})));
          }
          const missingLogos=await page.locator('[data-market-row] .company-logo.is-missing').count();
          await page.locator('[data-market-row] .company-logo img').first().evaluate(img=>img.dispatchEvent(new Event('error')));
          assert.equal(await page.locator('[data-market-row] .company-logo.is-missing').count(),missingLogos+1);
          await page.locator('[data-market-row] .company-logo img').first().evaluate(img=>img.closest('.company-logo').classList.remove('is-missing'));
          assert.ok(!(await page.locator('.market-hero').innerText()).includes('CDG'));
          const report=await (await context.request.get(new URL('report.json',base).href)).json();
          marketReport=report;
          if(report.cross_source_volume_audit?.publication_scope==='primary_only'){
            const warning=await page.locator('[data-market-integrity="primary-only"]').innerText();
            assert.ok(warning.includes('ne constitue pas une validation entre deux fournisseurs'));
            assert.equal(report.cross_source_volume_audit.cross_source_verified,false);
          }
          assert.equal(await page.locator('[data-market-row] [data-quote-clocks]').count(),80);
          const adi=report.results.find(r=>r.symbol==='ADI');
          const shown=adi.intraday_quote?.price??adi.price;
          const primary=page.locator('[data-quote-symbol="ADI"] [data-primary-price]');
          await assertQuote(primary,shown);
          if(report.market_overview?.official_reference){
            const counters=await page.locator('[data-market-counter-quality]').innerText();
            assert.ok(counters.replace(/\s/g,'').includes(String(report.market_overview.official_reference.contracts)+'contrats'));
            assert.ok(counters.includes('date propre n’est pas attestée'));
            assert.ok(counters.includes('revue manuellement'));
            if(report.cross_source_volume_audit?.publication_scope==='validated_title_lines')assert.ok((await page.locator('[data-market-integrity="detail-only"]').innerText()).includes('Total global corroboré'));
          }
          if(report.market_overview?.observed_at){
            const stamp=page.locator('.market-panel .collection-stamp time');
            assert.equal(new Date(await stamp.getAttribute('datetime')).getTime(),new Date(report.market_overview.observed_at).getTime());
            assert.ok((await stamp.innerText()).includes('Casablanca'));
          }
          await page.locator('#fundamental-explorer summary').click();
          assert.equal(await page.locator('[data-fundamental-row]:visible').count(),80);
          await page.locator('#fundamental-availability').selectOption('missing_annual');
          assert.equal(await page.locator('[data-fundamental-row]:visible').count(),report.results.filter(r=>!r.fundamental.exercise).length);
          await page.locator('#fundamental-reset').click();
          await page.locator('#fundamental-pe-max').fill('25');
          const selected=await page.locator('[data-fundamental-row]:visible').evaluateAll(rows=>rows.map(row=>JSON.parse(row.dataset.facts)));
          assert.ok(selected.length>0);
          assert.ok(selected.every(row=>Number.isFinite(row.pe)&&row.pe<=25));
          await page.locator('#fundamental-reset').click();
          assert.equal(await page.locator('[data-fundamental-row]:visible').count(),80);
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Fundamental explorer overflow '+width);
          await page.locator('#fundamental-explorer summary').click();
          await page.getByText('Suivi des mises à jour',{exact:true}).click();
          const publication=page.locator('[data-publication-commit]');
          await page.waitForFunction(()=>/^[a-f0-9]{40}$/.test(document.querySelector('[data-publication-commit]')?.textContent||''));
          assert.match(await publication.innerText(),/^[a-f0-9]{40}$/);
          const diagnostics=await page.locator('main').innerText();
          assert.ok(diagnostics.includes('Commit source des données historiques'));
          assert.ok(diagnostics.includes('Commit du générateur'));
          assert.ok(diagnostics.includes('Aucun conflit n’est résolu par écrasement automatique'));
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Expanded collection/provenance overflows '+width);
          await page.getByText('Suivi des mises à jour',{exact:true}).click();
        }
        if(route==='anomalies.html'){
          assert.equal(await page.locator('[data-anomaly-filter]').count(),4);
          await page.locator('[data-anomaly-filter="symbol"]').selectOption('ADI');
          const visible=await page.locator('[data-anomaly-row]:visible').evaluateAll(rows=>rows.map(r=>r.dataset.symbol));
          assert.ok(visible.length>0&&visible.every(s=>s==='ADI'));
          await page.locator('[data-anomaly-filter="symbol"]').selectOption('');
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Anomalies overflow '+width);
        }
        if(route.startsWith('titres/')){
          const symbol=route.split('/').pop().replace('.html','');
          const row=marketReport.results.find(r=>r.symbol===symbol);
          const shown=row.intraday_quote?.price??row.price;
          assert.equal(await page.locator('.issuer-quote [data-quote-clocks]').count(),1);
          await assertQuote(page.locator('.issuer-quote [data-primary-price]'),shown);
          assert.equal(await page.locator('.company-heading .company-logo img').count(),1);
          assert.ok(!(await page.locator('.issuer-quote').innerText()).includes('CDG'));
          assert.equal(await page.locator('.issuer-quote a').getAttribute('href'),'../sources.html#marche');
          if(marketReport.health?.checked_at){
            const stamp=page.locator('.issuer-quote .quote-collector-check .collection-stamp time');
            assert.equal(new Date(await stamp.getAttribute('datetime')).getTime(),new Date(marketReport.health.checked_at).getTime());
            assert.ok((await stamp.innerText()).includes('Casablanca'));
          }
          const dashboard=page.locator('[data-bi-dashboard]');
          await dashboard.locator('[data-bi-filters]').waitFor();
          const cards=dashboard.locator('[data-bi-metric]');
          const before=await cards.locator('strong').allTextContents();
          await dashboard.locator('#bi-group').selectOption('dette');
          assert.equal(await dashboard.locator('[data-bi-metric]:visible').count(),2);
          assert.equal(await dashboard.locator('[data-bi-explanation]:visible').count(),1);
          await dashboard.locator('#bi-group').selectOption('rentabilite');
          const roe=dashboard.locator('[data-bi-metric="roe_pct"]');
          await roe.focus();await page.keyboard.press('Enter');
          assert.equal(await roe.getAttribute('aria-pressed'),'true');
          assert.equal(await dashboard.locator('#bi-explain-roe_pct').isVisible(),true);
          assert.equal(await dashboard.locator('#bi-explain-pe').isVisible(),false);
          await dashboard.locator('#bi-group').selectOption('all');
          assert.deepEqual(await cards.locator('strong').allTextContents(),before);
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
          if(shots){fs.mkdirSync(shots,{recursive:true});await dashboard.screenshot({path:path.join(shots,`bi-${route.split('/')[1].split('.')[0]}-${width}.png`)});}
        }
        if(route==='titres/ENK.html'||route==='titres/CFGB.html'){
          const symbol=route.includes('ENK')?'ENK':'CFGB';
          const row=marketReport.results.find(r=>r.symbol===symbol);
          const key=symbol==='ENK'?'group_margin_pct':'cost_income_pct';
          const metric=row.sector_indicators.metrics[key];
          assert.equal(metric.status,'available');
          assert.equal(row.fundamental.pe,null,'Documentary restriction must remain');
          const item=page.locator(`[data-sector-metric="${key}"]`);
          assert.ok((await item.innerText()).includes(String(metric.value)));
          await item.locator('summary').click();
          assert.ok(await item.locator('a').count()>=3,'Primary inputs and method links');
          if(symbol==='ENK'){
            assert.ok((await item.innerText()).includes('sans conversion de change'));
            const nativeRoe=row.sector_indicators.metrics.native_group_roe_average_pct;
            assert.equal(nativeRoe.value,22.6412);
            assert.ok((await page.locator('[data-sector-metric="native_group_roe_average_pct"]').innerText()).includes('22.6412'));
          }
          else{
            const text=await item.innerText();
            assert.ok(text.includes('-513422')&&text.includes('-100560'),'Actual expense components retained');
          }
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Sector evidence overflow '+symbol+' '+width);
          if(width===375){
            for(const column of [0,1]){
              const box=await item.locator('td').nth(column).boundingBox();
              assert.ok(box&&box.x>=0&&box.x+box.width<=width+1,'Ratio label/value hidden by evidence scrolling '+symbol);
            }
          }
          if(shots)await page.locator('[data-sector-calculators]').screenshot({path:path.join(shots,`sector-${symbol}-${width}.png`)});
        }
        if(route==='titres/ADI.html'){
          const body=await page.locator('main').innerText();
          const currentReport=await (await context.request.get(new URL('report.json',base).href)).json();
          const currentAdi=currentReport.results.find(r=>r.symbol==='ADI').fundamental;
          const graph=page.locator('[data-chart-root]');
          await graph.locator('[data-chart-preset="price"]').click();
          await graph.locator('.chart-settings summary').click();
          for(const key of ['sma200','ema20','ema50','atr']){
            await page.locator(`[data-indicator="${key}"]`).click();
            assert.equal(await page.locator(`[data-indicator="${key}"]`).getAttribute('aria-pressed'),'true');
          }
          const chartText=await page.locator('[data-chart-readout]').innerText();
          for(const label of ['MM200','EMA20','EMA50','ATR Wilder'])assert.ok(chartText.includes(label),'Missing chart value '+label);
          assert.ok((await page.locator('#plot svg').innerHTML()).includes('ATR 14 · WILDER · MAD'));
          await page.getByText('Méthodes et différences entre plateformes',{exact:true}).click();
          assert.ok((await page.locator('main').innerText()).includes('Les cours ne sont pas ajustés aux opérations sur titres'));
          await page.getByText('Méthodes et différences entre plateformes',{exact:true}).click();
          await graph.locator('.chart-settings summary').click();
          await graph.locator('[data-chart-preset="momentum"]').click();
          assert.ok((await page.locator('#plot svg').innerHTML()).includes('MACD 12/26/9'));
          assert.ok((await page.locator('#plot svg').innerHTML()).includes('RSI 14'));
          await graph.locator('[data-chart-theme]').click();
          assert.equal(await graph.getAttribute('data-chart-theme'),'light');
          const contrasts=await graph.evaluate(root=>{
            const luminance=color=>{const rgb=color.match(/[\d.]+/g).slice(0,3).map(v=>{v=Number(v)/255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];};
            const background=luminance(getComputedStyle(root).backgroundColor);
            return ['.chart-help summary','.chart-readout .gain,.chart-readout .loss','.chart-info','.chart-gesture-hint'].map(selector=>{
              const text=luminance(getComputedStyle(root.querySelector(selector)).color);
              return (Math.max(text,background)+.05)/(Math.min(text,background)+.05);
            });
          });
          assert.ok(contrasts.every(ratio=>ratio>=4.5),'Light chart text contrast below 4.5: '+contrasts.join(','));
          // Real user taps at price coordinates create personal lines, never facts.
          await graph.locator('[data-chart-tool="level"]').click();
          await page.locator('#plot').click({position:{x:80,y:95}});
          assert.equal(await page.locator('#plot .chart-annotation').count(),1);
          await graph.locator('[data-chart-tool="trend"]').click();
          await page.locator('#plot').click({position:{x:85,y:130}});
          await page.locator('#plot').click({position:{x:160,y:85}});
          assert.equal(await page.locator('#plot .chart-annotation').count(),2);
          const annotations=await page.evaluate(()=>JSON.parse(localStorage.getItem('nour-chart-drawings-v1:ADI')));
          assert.equal(annotations.length,2);
          const actual=await (await context.request.get(new URL('report.json',base).href)).json();
          assert.deepEqual(actual.results.find(r=>r.symbol==='ADI').fundamental,currentAdi);
          await page.reload({waitUntil:'networkidle'});
          assert.equal(await graph.getAttribute('data-chart-theme'),'light');
          assert.equal(await page.locator('#plot .chart-annotation').count(),2);
          assert.ok((await page.locator('#plot svg').innerHTML()).includes('MACD 12/26/9'));
          const downloadEvent=page.waitForEvent('download');
          await graph.locator('[data-chart-export]').click();
          const exported=await downloadEvent;
          assert.match(exported.suggestedFilename(),/^Nour-ADI-\d{4}-\d{2}-\d{2}\.svg$/);
          const xml=fs.readFileSync(await exported.path(),'utf8');
          assert.ok(xml.includes('Cours non ajustés'));
          assert.ok(xml.includes('chart-annotation'));
          assert.ok(xml.includes('MACD 12/26/9'));
          await graph.locator('[data-chart-undo]').click();
          assert.equal(await page.locator('#plot .chart-annotation').count(),1);
          if(shots){fs.mkdirSync(shots,{recursive:true});await page.locator('#graphique').screenshot({path:path.join(shots,`chart-workspace-light-${width}.png`)});}
          await graph.locator('[data-chart-theme]').click();
          await page.locator('.issuer-nav a[href="#fondamentaux"]').click();
          assert.equal(await page.locator('#fondamentaux').isVisible(),true);
          assert.ok(await page.locator('.financial-history').count()>0);
          if(shots)await page.locator('.financial-history-grid').screenshot({path:path.join(shots,`financial-history-${width}.png`)});
          if(currentAdi.debt_reconciliation?.status==='unresolved')assert.ok(body.includes('Dette nette à rapprocher — ratios suspendus'));
          if(currentAdi.roe_average_equity_pct!==null)assert.ok(body.includes('ROE sur fonds propres moyens : '+currentAdi.roe_average_equity_pct.toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' %'));
          assert.ok(body.includes('Groupe de comparaison : Promoteurs immobiliers'));
          const riskHelp=page.locator('#risk-help');
          assert.equal(await riskHelp.evaluate(el=>el.open),false);
          await page.getByRole('button',{name:'Assistant Nour',exact:true}).waitFor();
          await page.getByText('Le risque, en langage simple',{exact:true}).click();
          assert.ok((await riskHelp.innerText()).includes('Une perte future peut être plus forte'));
          assert.equal(await riskHelp.evaluate(el=>el.open),true);
          await page.locator('#risk-help summary').focus();
          await page.keyboard.press('Enter');
          assert.equal(await riskHelp.evaluate(el=>el.open),false);
          await page.getByText('Pourquoi cette comparaison est-elle disponible ou absente ?', {exact:true}).click();
          assert.ok((await page.locator('main').innerText()).includes('Nous exigeons quatre autres ratios compatibles'));
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
          if(shots){fs.mkdirSync(shots,{recursive:true});await page.screenshot({path:path.join(shots,`adi-quality-${width}.png`),fullPage:true});}
        }
        if(route==='titres/MNG.html'||route==='titres/MUT.html'){
          const symbol=route.split('/')[1].split('.')[0];
          const currentReport=await (await context.request.get(new URL('report.json',base).href)).json();
          const f=currentReport.results.find(r=>r.symbol===symbol).fundamental;
          const body=await page.locator('main').innerText();
          if(f.debt_reconciliation.status==='scope_reconciled')assert.ok(body.includes('Dette : périmètres rapprochés'));
          if(f.debt_reconciliation.status==='unresolved')assert.ok(body.includes('Dette nette à rapprocher — ratios suspendus'));
          if(f.debt_reconciliation.primary_review?.conclusion){
            await page.getByText('Preuves du contrôle de dette',{exact:true}).click();
            assert.ok((await page.locator('main').innerText()).includes(f.debt_reconciliation.primary_review.conclusion));
          }
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
          if(shots){fs.mkdirSync(shots,{recursive:true});await page.screenshot({path:path.join(shots,`debt-${symbol}-${width}.png`),fullPage:true});}
        }
        if(route==='sources.html'){
          assert.ok((await page.locator('#marche').innerText()).includes('CDG Capital Bourse'));
          assert.ok((await page.locator('#logos summary').innerText()).includes('Logos des sociétés'));
          const body=await page.locator('main').innerText();
          for(const name of ['Sources officielles marocaines','Bank Al-Maghrib','Maroclear','Autorité de contrôle des assurances','Office des Changes']){
            assert.ok(body.includes(name),'Missing economic source '+name);
          }
          const summary=await (await context.request.get(new URL('economic-sources-summary.json',base).href)).json();
          // Institutions may grow as official sources are curated: verify parity,
          // not a stale fixed count from an older source catalog.
          assert.ok(Number.isInteger(summary.institution_count)&&summary.institution_count>=36);
          // The next table belongs to the seven sector-source monitors, not to the institution registry.
          assert.equal(await page.locator('main table').first().locator('tbody tr').count(),summary.institution_count);
          assert.equal(summary.auto_import_enabled,false);
          assert.equal(summary.usable_to_certify_issuer_financial_facts,false);
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Sources page overflows '+width);
        }
        if(route==='metiers.html'){
          const body=await page.locator('main').innerText();
          for(const label of ['Analyse par métier','Blocages à rapprocher','TGCC','SGTM','CMGP','Documents']){
            if(label==='Documents')continue;
            assert.ok(body.includes(label),'Missing métier review: '+label);
          }
          assert.equal(await page.locator('table').count(),2);
          assert.equal(await page.locator('table').last().locator('tbody tr').count(),80);
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Métier page overflows '+width);
          const json=await (await context.request.get(new URL('sector-readiness.json',base).href)).json();
          assert.equal(json.universe,80);
          assert.equal(json.curated,78);
          assert.equal(json.documents_certified,false);
          const publishedReport=await (await context.request.get(new URL('report.json',base).href)).json();
          // Review progress changes the reasons, not the visibility contract:
          // every unresolved numerator or documentary restriction is queued.
          for(const row of publishedReport.results){
            for(const check of row.fundamental.financial_audit.checks){
              if(check.status==='blocked'&&['group_earnings_missing_total_not_substituted','documentary_reconciliation_pending'].includes(check.code)){
                const action=json.review_queue.find(x=>x.symbol===row.symbol&&x.code===check.code);
                assert.ok(action,'Missing canonical review action '+row.symbol+' '+check.code);
                assert.deepEqual(action.blocked_metrics,check.blocked_metrics);
                assert.ok(action.source_pages_to_check.length>0);
              }
            }
          }
          if(shots){fs.mkdirSync(shots,{recursive:true});await page.screenshot({path:path.join(shots,`metiers-${width}.png`),fullPage:true});}
        }
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
        assert.equal(await page.locator('#assistant-ai-option').isVisible(),true,
          JSON.stringify(await page.evaluate(async()=>({
            config:await fetch('assistant-config.json').then(r=>r.json()).catch(e=>String(e)),
            optionHidden:document.getElementById('assistant-ai-option')?.hidden,
            optionStyle:getComputedStyle(document.getElementById('assistant-ai-option')).display,
            scriptUrl:[...document.scripts].find(x=>x.src.includes('assistant.js'))?.src
          }))));
        assert.equal(await page.locator('#assistant-access-option').isVisible(),false);
        const expected=route.startsWith('titres/')?route.split('/')[1].split('.')[0]:'MASI';
        assert.equal(await page.locator('#assistant-symbol').inputValue(),expected);
        await page.locator('#assistant-symbol').selectOption('JET');
        await page.locator('[data-assistant-question="Quels fondamentaux sont disponibles ?"]').click();
        await page.getByText('PER :',{exact:false}).last().waitFor();
        const report=await (await context.request.get(new URL('report.json',base).href)).json();
        const jet=report.results.find(row=>row.symbol==='JET');
        const messages=await page.locator('#assistant-messages').innerText();
        assert.ok(messages.includes(answerNumber(jet.fundamental.pe)));
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
        await page.getByText('MM50 : '+answerNumber(adi.technical.sma50),{exact:false}).last().waitFor();
        assert.equal(await page.locator('#assistant-symbol').inputValue(),'ADI');
        await page.locator('#assistant-question').fill('Et son RSI ?');
        await page.getByRole('button',{name:'Envoyer',exact:true}).click();
        await page.getByText('RSI 14 : '+answerNumber(adi.technical.rsi14),{exact:false}).last().waitFor();
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
          const screening=await ask('Les 5 PER les plus faibles en 2025');
          assert.ok(screening.includes('titre(s) correspondant(s) sur 80'));
          assert.ok(screening.includes('PER annuel :'));
          assert.ok(screening.includes('ne constitue pas une comparaison sectorielle validée'));
          const combined=await ask('Cours, PER, RSI et VaR ADI');
          for(const heading of ['fondamentaux','technique','risques','cours'])assert.ok(combined.includes(heading));
          for(const [label,n] of [['Clôture : ',adi.price],['PER : ',adi.fundamental.pe],['RSI 14 : ',adi.technical.rsi14],['VaR historique 95 % · 1 séance : ',adi.market_risk.tail_risk.var95_loss_pct]])assert.ok(combined.includes(label+answerNumber(n)),label+combined);
          const bands=await ask('Bandes de Bollinger ADI');
          assert.ok(bands.includes(answerNumber(adi.technical.bollinger_upper)));
          assert.ok(bands.includes(answerNumber(adi.technical.bollinger_lower)));
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Assistant queries overflow '+width);
          const risk=await ask('Quels risques pour ADI face au MASI ?');
          assert.ok(risk.includes('Bêta : '+answerNumber(adi.market_risk.beta)));
          assert.equal(await page.locator('#assistant-symbol').inputValue(),'ADI');
          const definition=await ask('Que veut dire bêta ?');
          assert.ok(definition.includes(facts.knowledge.definitions.beta));
          assert.ok(definition.includes('ADI · Alliances'));
          const tailAnswer=await ask('Quelle VaR historique pour ADI ?');
          const tail=adi.market_risk.tail_risk;
          const value=answerNumber(tail.var95_loss_pct);
          assert.ok(tailAnswer.includes('VaR historique 95 % · 1 séance : '+value));
          assert.ok(tailAnswer.includes('pas une perte maximale'));
          await ask('Compare le PER d’ADI et RDS');
          const comparison=await ask('Et leur BPA ?');
          for(const s of ['ADI','RDS']){
            assert.ok(comparison.includes(s+' ·'));
            const eps=facts.symbols[s].fundamental.eps_mad;
            assert.ok(comparison.includes('BPA : '+(answerNumber(eps))));
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
        if(width===1440&&route==='index.html'){
          assert.ok(rect.width>=800,'Desktop dialog should use a readable width.');
          await page.locator('#assistant-expand').click();
          assert.equal(await page.locator('#assistant-expand').getAttribute('aria-pressed'),'true');
          const large=await page.locator('#assistant-dialog').boundingBox();
          assert.ok(large.width>rect.width&&large.x>=0&&large.x+large.width<=width+1);
          await page.locator('#assistant-expand').click();
          assert.equal(await page.locator('#assistant-expand').getAttribute('aria-pressed'),'false');
        }
        await page.getByRole('button',{name:'Effacer',exact:true}).click();
        assert.equal(await page.locator('.assistant-message').count(),0);
        await page.locator('#assistant-question').fill('<img src=x onerror=alert(1)> MASI le 31/03/26');
        await page.getByRole('button',{name:'Envoyer',exact:true}).click();
        await page.getByText('Clôture du 2026-03-31 :',{exact:false}).waitFor();
        assert.equal(await page.locator('#assistant-messages img').count(),0);
        assert.equal(await page.locator('#assistant-ai').isChecked(),false);
        if(route==='index.html'){
          let validated=0,simulateUnavailable=false;
          await page.route('https://bvc-nour-assistant.abdmoutalib207.workers.dev/api/assistant',async intercepted=>{
            const req=intercepted.request();
            if(req.method()==='OPTIONS'){
              await intercepted.fulfill({status:204,headers:{
                'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'POST, OPTIONS',
                'Access-Control-Allow-Headers':'Content-Type, Authorization'}});
              return;
            }
            assert.equal(req.headers()['authorization'],'Bearer '+'X'.repeat(32));
            const payload=req.postDataJSON();
            assert.equal(payload.consent,true);
            assert.match(payload.snapshot_id,/^[a-f0-9]{64}$/);
            assert.ok(payload.question.includes('ADI'));
            validated++;
            await intercepted.fulfill({status:200,contentType:'application/json',headers:{'Access-Control-Allow-Origin':'*'},
              body:JSON.stringify(simulateUnavailable?{mode:'unavailable',error:'IA de test indisponible'}:{mode:'llm',text:'Explication de test sans calcul',sources:[]})});
          });
          await page.locator('#assistant-ai').check();
          assert.equal(await page.locator('#assistant-access-option').isVisible(),true);
          assert.equal(await page.locator('#assistant-remember').isChecked(),false);
          await page.locator('#assistant-question').fill('Explique ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.getByText('Renseignez votre code privé Cloudflare',{exact:false}).waitFor();
          assert.equal(validated,0);
          await page.locator('#assistant-access').fill('X'.repeat(32));
          await page.locator('#assistant-question').fill('Explique ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.getByText('Explication de test sans calcul',{exact:true}).waitFor();
          assert.equal(validated,1);
          assert.equal(await page.locator('#assistant-access').inputValue(),'');
          assert.equal(await page.locator('#assistant-access-active').isVisible(),true);
          await page.getByRole('button',{name:'Effacer',exact:true}).click();
          assert.equal(await page.locator('#assistant-access-active').isVisible(),true);
          await page.locator('#assistant-question').fill('Explique ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.waitForFunction(()=>document.querySelector('#assistant-send').disabled===false);
          assert.equal(validated,2);
          await page.locator('#assistant-ai').uncheck();
          assert.equal(await page.locator('#assistant-access-option').isVisible(),false);
          await page.locator('#assistant-ai').check();
          assert.equal(await page.locator('#assistant-access-active').isVisible(),true);
          await page.getByRole('button',{name:'Fermer l’assistant'}).click();
          await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
          assert.equal(await page.locator('#assistant-access-active').isVisible(),true);
          await page.locator('#assistant-question').fill('Explique ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.waitForFunction(()=>document.querySelector('#assistant-send').disabled===false);
          assert.equal(validated,3);
          await page.locator('#assistant-forget').click();
          assert.equal(await page.locator('#assistant-access-active').isVisible(),false);
          assert.equal(await page.locator('#assistant-access-option').isVisible(),true);
          await page.locator('#assistant-question').fill('Explique ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.getByText('Renseignez votre code privé Cloudflare',{exact:false}).last().waitFor();
          assert.equal(validated,3);
          simulateUnavailable=true;
          await page.locator('#assistant-access').fill('X'.repeat(32));
          await page.locator('#assistant-question').fill('Explique le PER ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.getByText('IA de test indisponible',{exact:true}).waitFor();
          assert.ok((await page.locator('#assistant-messages').innerText()).includes('Consultation locale Nour · aucune réponse IA produite'));
          assert.equal(validated,4);
          simulateUnavailable=false;
          // Without opt-in a refresh must still forget the page-only code.
          await page.reload({waitUntil:'networkidle'});
          await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
          await page.getByText('Données chargées · analyse du',{exact:false}).waitFor();
          await page.locator('#assistant-ai').check();
          assert.equal(await page.locator('#assistant-access-option').isVisible(),true);
          assert.equal(await page.locator('#assistant-remember').isChecked(),false);
          await page.locator('#assistant-remember').check();
          await page.locator('#assistant-access').fill('X'.repeat(32));
          await page.locator('#assistant-question').fill('Explique le PER ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.getByText('Explication de test sans calcul',{exact:true}).waitFor();
          assert.equal(validated,5);
          assert.equal(await page.evaluate(()=>Object.keys(localStorage).some(k=>k.startsWith('nour.assistant.'))),false);
          await page.reload({waitUntil:'networkidle'});
          await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
          await page.getByText('Données chargées · analyse du',{exact:false}).waitFor();
          assert.equal(await page.locator('#assistant-ai').isChecked(),false,'access restoration must not restore AI consent');
          await page.locator('#assistant-ai').check();
          assert.equal(await page.locator('#assistant-access-active').isVisible(),true);
          assert.equal(await page.locator('#assistant-access').inputValue(),'');
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Remembered access overflows '+width);
          if(shots){fs.mkdirSync(shots,{recursive:true});await page.screenshot({path:path.join(shots,`assistant-tab-access-${width}.png`)});}
          await page.locator('#assistant-question').fill('Explique le PER ADI');
          await page.getByRole('button',{name:'Envoyer',exact:true}).click();
          await page.waitForFunction(()=>document.querySelector('#assistant-send').disabled===false);
          assert.equal(validated,6);
          // Same tab, another issuer page, same validated access.
          await page.goto(new URL('titres/ADI.html',base).href,{waitUntil:'networkidle'});
          await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
          await page.getByText('Données chargées · analyse du',{exact:false}).waitFor();
          await page.locator('#assistant-ai').check();
          assert.equal(await page.locator('#assistant-access-active').isVisible(),true);
          await page.locator('#assistant-forget').click();
          assert.equal(await page.evaluate(()=>sessionStorage.getItem('nour.assistant.tab-access.v1')),null);
          await page.reload({waitUntil:'networkidle'});
          await page.getByRole('button',{name:'Assistant Nour',exact:true}).click();
          await page.getByText('Données chargées · analyse du',{exact:false}).waitFor();
          await page.locator('#assistant-ai').check();
          assert.equal(await page.locator('#assistant-access-option').isVisible(),true);
          assert.equal(await page.locator('#assistant-remember').isChecked(),false);
          await page.locator('#assistant-ai').uncheck();
        }
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
      await native.goto(new URL('titres/ADI.html',base).href);
      const nativeRisk=native.locator('#risk-help');
      await native.locator('#risk-help summary').click();
      assert.equal(await nativeRisk.evaluate(el=>el.open),true);
      assert.ok((await nativeRisk.innerText()).includes('Une perte future peut être plus forte'));
      await native.locator('#risk-help summary').focus();
      await native.keyboard.press('Enter');
      assert.equal(await nativeRisk.evaluate(el=>el.open),false);
      await nojs.close();
    }
    console.log(`Browser QA: ${interactions} page/viewport journeys; natural definitions, comparison and semester follow-ups, benchmark MASI subject, global briefing, lab parity, cost/horizon follow-up, full CSV date/volume follow-up and explicit context reset; laboratory help and no-JS at 3 widths; no LLM call.`);
  }finally{if(shots){fs.mkdirSync(shots,{recursive:true});fs.writeFileSync(path.join(shots,'browser-anomalies.json'),JSON.stringify(assetAnomalies,null,2));}console.log('Nonblocking branding observations: '+assetAnomalies.length);await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
