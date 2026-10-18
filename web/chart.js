/* Client-only chart: validated OHLCV, no remote scripts and no scoring side effects. */
(() => {
  'use strict';
  const root = document.querySelector('[data-chart-root]');
  if (!root) return;
  const holder = root.querySelector('#plot');
  const readout = root.querySelector('[data-chart-readout]');
  const info = root.querySelector('#chart-info');
  const fmt = value => new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2}).format(value);
  const safe = value => Number.isFinite(value) ? value.toFixed(2) : '—';
  const tickDate = (date,width) => width<450 ? `${date.slice(8)}/${date.slice(5,7)}/${date.slice(2,4)}` : date;
  let raw;
  try { raw = JSON.parse(root.querySelector('#history-data').textContent); } catch { return; }
  const bars = raw.filter(b => Array.isArray(b) && /^\d{4}-\d{2}-\d{2}$/.test(b[0]) &&
    b.length === 6 && b.slice(1).every(v => typeof v === 'number' && Number.isFinite(v)) &&
    b[3] > 0 && b[2] >= Math.max(b[1], b[3], b[4]) && b[3] <= Math.min(b[1], b[4]) && b[5] >= 0);
  if (!bars.length) return;

  const since = root.dataset.indicatorSince || '';
  const series = window.NourCharts.indicators(bars, since);

  const symbol = root.closest('[data-chart-symbol]')?.dataset.chartSymbol || 'titre';
  const allowed = ['volume','sma20','sma50','sma200','ema20','ema50','bands','rsi','macd','atr'];
  const settingsKey='nour-chart-view-v1', drawingsKey='nour-chart-drawings-v1:'+symbol;
  let saved={},drawings=[],storageReady=true;
  try {
    const settings=localStorage.getItem(settingsKey),stored=localStorage.getItem(drawingsKey);
    if(settings&&settings.length<4000)saved=JSON.parse(settings)||{};
    if(stored&&stored.length<20000){
      const parsed=JSON.parse(stored),dates=new Set(bars.map(b=>b[0]));
      if(Array.isArray(parsed))drawings=parsed.slice(-40).filter(d=>
        d&&['level','trend'].includes(d.type)&&Array.isArray(d.points)&&d.points.length===(d.type==='level'?1:2)&&
        d.points.every(p=>Array.isArray(p)&&p.length===2&&dates.has(p[0])&&Number.isFinite(p[1])&&p[1]>0&&p[1]<1e12));
    }
  }catch{saved={};drawings=[];storageReady=false;}
  const state = Object.assign(new window.NourCharts.Viewport(bars.length, Math.min(252,bars.length)),
    {type:saved.type==='line'?'line':'candles', period:'252', indicators:new Set(Array.isArray(saved.indicators)?saved.indicators.filter(k=>allowed.includes(k)):['volume']), selected:null});
  root.dataset.chartTheme=saved.theme==='light'?'light':'dark';
  let explorer, selectBar = () => {},pickPoint=()=>null,tool='cursor',draft=null;
  const status=root.querySelector('[data-chart-drawing-status]');
  const save=()=>{
    try{
      localStorage.setItem(settingsKey,JSON.stringify({type:state.type,indicators:[...state.indicators],theme:root.dataset.chartTheme}));
      localStorage.setItem(drawingsKey,JSON.stringify(drawings));
    }catch{storageReady=false;}
    if(!storageReady&&status)status.textContent='Stockage indisponible : réglages et tracés conservés uniquement dans cette page.';
  };
  const setTool=key=>{
    tool=key;draft=null;
    root.querySelectorAll('[data-chart-tool]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.chartTool===tool)));
    if(status)status.textContent=key==='level'?'Touchez un prix pour poser un niveau.':key==='trend'?'Choisissez deux points dans la zone des prix.':
      storageReady?'Tracés personnels, conservés sur cet appareil.':'Stockage indisponible : tracés conservés dans cette page.';
  };
  const periodButtons = [...root.querySelectorAll('[data-period]')];
  const toggleButtons = [...root.querySelectorAll('[data-indicator]')];
  const modeButtons = [...root.querySelectorAll('[data-chart-type]')];
  const updateButtons = () => {
    periodButtons.forEach(b => b.setAttribute('aria-pressed', String(state.period === b.dataset.period)));
    toggleButtons.forEach(b => b.setAttribute('aria-pressed', String(state.indicators.has(b.dataset.indicator))));
    modeButtons.forEach(b => b.setAttribute('aria-pressed', String(state.type === b.dataset.chartType)));
    root.querySelectorAll('[data-chart-preset]').forEach(b=>{
      const expected=b.dataset.chartPreset==='trend'?['volume','sma20','sma50']:b.dataset.chartPreset==='momentum'?['volume','rsi','macd']:['volume'];
      b.setAttribute('aria-pressed',String(expected.length===state.indicators.size&&expected.every(key=>state.indicators.has(key))));
    });
    const theme=root.querySelector('[data-chart-theme]');
    if(theme){theme.textContent=root.dataset.chartTheme==='light'?'Fond sombre':'Fond clair';theme.setAttribute('aria-pressed',String(root.dataset.chartTheme==='light'));}
    const undo=root.querySelector('[data-chart-undo]');if(undo)undo.disabled=drawings.length===0;
  };
  const path = (points, x, y) => {
    let opened = false;
    return points.map((p, j) => {
      if (p === null || !Number.isFinite(p)) { opened = false; return ''; }
      const part = `${opened ? 'L' : 'M'}${x(j).toFixed(1)},${y(p).toFixed(1)}`;
      opened = true;
      return part;
    }).join(' ');
  };
  const clamp = (v, low, high) => Math.max(low, Math.min(high, v));

  function render() {
    updateButtons();
    const start = Math.max(0, state.end - state.count);
    const visible = bars.slice(start, state.end);
    const derived = series.slice(start, state.end);
    if (!visible.length) return;
    const W = Math.max(240,Math.round(holder.clientWidth || 900));
    const light=root.dataset.chartTheme==='light';
    const L = W<450?12:20, R = W-(W<450?62:76), plotW = R - L, top = 28;
    const full=document.fullscreenElement===root||root.classList.contains('chart-expanded');
    const priceH=full?Math.max(280,Math.min(620,innerHeight*.53)):(W>900?390:W>600?330:285);
    holder.dataset.plotLeft=L; holder.dataset.plotRight=R;
    const volumeOn = state.indicators.has('volume');
    const volumeY = top + priceH + 20;
    const rsiY = volumeY + (volumeOn ? 65 : 5);
    const rsiOn = state.indicators.has('rsi');
    const macdY = rsiY + (rsiOn ? 101 : 0);
    const macdOn = state.indicators.has('macd');
    const atrY = macdY + (macdOn ? 103 : 0);
    const atrOn = state.indicators.has('atr');
    const height = atrY + (atrOn ? 92 : 0) + 25;
    const x = j => L + (j + .5) * plotW / visible.length;
    const priceValues = visible.flatMap(b => state.type === 'candles' ? [b[2], b[3]] : [b[4]]);
    if (state.indicators.has('sma20')) priceValues.push(...derived.map(d => d.sma20).filter(v => v !== null));
    if (state.indicators.has('sma50')) priceValues.push(...derived.map(d => d.sma50).filter(v => v !== null));
    for(const key of ['sma200','ema20','ema50']) if(state.indicators.has(key)) priceValues.push(...derived.map(d=>d[key]).filter(v=>v!==null));
    if (state.indicators.has('bands')) priceValues.push(...derived.flatMap(d => [d.upper, d.lower]).filter(v => v !== null));
    let lo = Math.min(...priceValues), hi = Math.max(...priceValues);
    const pad = (hi - lo) * .08 || Math.max(hi * .01, .01);
    lo -= pad; hi += pad;
    const yp = v => top + priceH * (hi - v) / (hi - lo);
    const axes = [0,1,2,3,4].map(j => {
      const yy = top + priceH * j / 4;
      return `<line x1="${L}" x2="${R}" y1="${yy}" y2="${yy}" class="chart-grid"/><text x="${R+6}" y="${yy+4}">${fmt(hi-(hi-lo)*j/4)}</text>`;
    }).join('');
    const dateGrid=[0,1,2,3,4].map(n=>{
      const j=Math.round((visible.length-1)*n/4),xx=x(j);
      return `<line x1="${xx}" x2="${xx}" y1="${top}" y2="${height-22}" class="chart-grid chart-date-grid"/>`+
        (W>600||n%2===0?`<text x="${xx}" y="${height-5}" text-anchor="${n===0?'start':n===4?'end':'middle'}">${tickDate(visible[j][0],W)}</text>`:'');
    }).join('');
    const closePath = path(visible.map(b => b[4]), x, yp);
    const candleWidth = clamp(plotW / visible.length * .65, .65, 11);
    const candles = visible.map((b,j) => {
      const up = b[4] >= b[1], yy = Math.min(yp(b[1]), yp(b[4]));
      return `<g class="${up ? 'candle-up' : 'candle-down'}"><line x1="${x(j)}" x2="${x(j)}" y1="${yp(b[2])}" y2="${yp(b[3])}"/><rect x="${x(j)-candleWidth/2}" y="${yy}" width="${candleWidth}" height="${Math.max(1,Math.abs(yp(b[1])-yp(b[4])))}"/></g>`;
    }).join('');
    const price = state.type === 'candles' ? candles :
      `<path class="price-line" d="${closePath}"/>`;
    const overlay = (key, color) => `<path d="${path(derived.map(d=>d[key]),x,yp)}" fill="none" stroke="${color}" stroke-width="1.8" vector-effect="non-scaling-stroke"/>`;
    let indicators = '';
    if (state.indicators.has('bands')) indicators += overlay('upper',light?'#7551bb':'#a18feb') + overlay('lower',light?'#7551bb':'#a18feb');
    if (state.indicators.has('sma20')) indicators += overlay('sma20',light?'#9c6508':'#f3ce77');
    if (state.indicators.has('sma50')) indicators += overlay('sma50',light?'#087f9c':'#5ac9de');
    for(const [key,color] of [['sma200',light?'#a34451':'#e99f9f'],['ema20',light?'#387925':'#a7df80'],['ema50',light?'#a76018':'#f5a85c']]) if(state.indicators.has(key)) indicators += overlay(key,color);
    if (volumeOn) {
      const maxVolume = Math.max(1,...visible.map(b=>b[5]));
      const width = clamp(plotW/visible.length*.7,.7,9);
      indicators += `<text x="${L}" y="${volumeY-3}">VOLUMES</text>` + visible.map((b,j) =>
        `<rect class="volume-bar" x="${x(j)-width/2}" y="${volumeY+50-45*b[5]/maxVolume}" width="${width}" height="${Math.max(1,45*b[5]/maxVolume)}"/>`).join('');
    }
    if (rsiOn) {
      const yr = v => rsiY + 74 * (100-v)/100 + 14;
      indicators += `<text x="${L}" y="${rsiY+8}">RSI 14</text>` +
        [30,70].map(level => `<line class="chart-threshold" x1="${L}" x2="${R}" y1="${yr(level)}" y2="${yr(level)}"/><text x="${R+5}" y="${yr(level)+4}">${level}</text>`).join('') +
        `<path d="${path(derived.map(d=>d.rsi),x,yr)}" fill="none" stroke="${light?'#7750bc':'#c9a3f1'}" stroke-width="1.8"/>`;
    }
    if (macdOn) {
      const values = derived.flatMap(d=>[d.macd,d.signal]).filter(v=>v!==null);
      const hist = derived.map(d=>d.macd!==null && d.signal!==null ? d.macd-d.signal : null).filter(v=>v!==null);
      const bound = Math.max(.01,...values.map(Math.abs),...hist.map(Math.abs));
      const ym = v => macdY + 55 - v/bound*36;
      const width = clamp(plotW/visible.length*.7,.7,9);
      indicators += `<text x="${L}" y="${macdY+10}">MACD 12/26/9</text><line class="chart-threshold" x1="${L}" x2="${R}" y1="${ym(0)}" y2="${ym(0)}"/>` +
        derived.map((d,j)=> d.macd===null || d.signal===null ? '' :
          `<rect class="${d.macd-d.signal>=0 ? 'hist-up' : 'hist-down'}" x="${x(j)-width/2}" y="${Math.min(ym(0),ym(d.macd-d.signal))}" width="${width}" height="${Math.max(1,Math.abs(ym(d.macd-d.signal)-ym(0)))}"/>`).join('') +
        `<path d="${path(derived.map(d=>d.macd),x,ym)}" fill="none" stroke="${light?'#087f9c':'#83d6e5'}" stroke-width="1.8"/>` +
        `<path d="${path(derived.map(d=>d.signal),x,ym)}" fill="none" stroke="${light?'#9c6508':'#f3ce77'}" stroke-width="1.5"/>`;
    }
    if(atrOn){
      const bound=Math.max(.01,...derived.map(d=>d.atr14_wilder).filter(v=>v!==null));
      const ya=v=>atrY+78-v/bound*55;
      indicators+=`<text x="${L}" y="${atrY+12}">ATR 14 · WILDER · MAD</text><line class="chart-threshold" x1="${L}" x2="${R}" y1="${ya(0)}" y2="${ya(0)}"/>`+
        `<path d="${path(derived.map(d=>d.atr14_wilder),x,ya)}" fill="none" stroke="${light?'#387925':'#a7df80'}" stroke-width="1.8"/>`;
    }
    const comparison=explorer?.selection();
    const range = comparison ? comparison.map(i=>clamp(i-start,0,visible.length-1)).sort((a,b)=>a-b) : null;
    const highlight=range ? `<rect x="${x(range[0])}" y="${top}" width="${x(range[1])-x(range[0])}" height="${priceH}" fill="#f3ce77" opacity=".1"/>` : '';
    const coordinates=p=>{
      const i=bars.findIndex(b=>b[0]===p[0]);
      return [L+(i-start+.5)*plotW/visible.length,yp(p[1])];
    };
    const annotation=(d,index)=>{
      const [a,b]=d.points.map(coordinates),label=`Tracé ${index+1}`;
      if(d.type==='level')return `<g class="chart-annotation"><line x1="${L}" x2="${R}" y1="${a[1]}" y2="${a[1]}"/><text x="${L+5}" y="${a[1]-5}">${label} · ${fmt(d.points[0][1])} MAD</text></g>`;
      return `<g class="chart-annotation"><line x1="${a[0]}" x2="${b[0]}" y1="${a[1]}" y2="${b[1]}"/><circle cx="${a[0]}" cy="${a[1]}" r="3"/><circle cx="${b[0]}" cy="${b[1]}" r="3"/></g>`;
    };
    const annotations=drawings.map(annotation).join('')+(draft?`<circle class="chart-draft" cx="${coordinates(draft)[0]}" cy="${coordinates(draft)[1]}" r="5"/>`:'');
    const last=visible.at(-1)[4];
    holder.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${height}" role="img" aria-label="Graphique OHLCV de ${visible.length} séances"><defs><clipPath id="price-clip"><rect x="${L}" y="${top}" width="${plotW}" height="${priceH}"/></clipPath></defs>${axes}${dateGrid}${highlight}<g clip-path="url(#price-clip)">${price}</g>${indicators}<line x1="${L}" x2="${R}" y1="${yp(last)}" y2="${yp(last)}" class="chart-last-price"/><g clip-path="url(#price-clip)">${annotations}</g><line class="chart-cross" x1="0" x2="0" y1="${top}" y2="${height-22}" visibility="hidden"/><line class="chart-cross-price" x1="${L}" x2="${R}" y1="0" y2="0" visibility="hidden"/><circle class="chart-point" cx="0" cy="0" r="4" visibility="hidden"/><g class="chart-price-tag" visibility="hidden"><rect x="${R+3}" y="0" width="${W-R-4}" height="20" rx="3"/><text x="${R+6}" y="0"></text></g></svg>`;
    pickPoint=(i,event)=>{
      const rect=holder.getBoundingClientRect(),yy=(event.clientY-rect.top)*height/rect.height;
      if(yy<top||yy>top+priceH)return null;
      const value=hi-(yy-top)*(hi-lo)/priceH;
      return value>0?[bars[i][0],value]:null;
    };
    info.textContent = `${visible[0][0]} → ${visible.at(-1)[0]} · ${visible.length} séances · ${fmt(lo+pad)} à ${fmt(hi-pad)} MAD` +
      (Number(root.dataset.invalidCount) ? ` · ${root.dataset.invalidCount} séance(s) OHLCV écartée(s)` : '');
    const svg = holder.querySelector('svg'), cross = svg.querySelector('.chart-cross'), dot = svg.querySelector('.chart-point');
    const priceCross=svg.querySelector('.chart-cross-price'), tag=svg.querySelector('.chart-price-tag');
    function select(j, announce=false) {
      j = clamp(j,0,visible.length-1);
      state.selected = start+j;
      const b=visible[j], d=derived[j], xx=x(j);
      cross.setAttribute('x1',xx); cross.setAttribute('x2',xx); cross.setAttribute('visibility','visible');
      dot.setAttribute('cx',xx); dot.setAttribute('cy',yp(b[4])); dot.setAttribute('visibility','visible');
      priceCross.setAttribute('y1',yp(b[4]));priceCross.setAttribute('y2',yp(b[4]));priceCross.setAttribute('visibility','visible');
      tag.setAttribute('visibility','visible');tag.querySelector('rect').setAttribute('y',yp(b[4])-10);
      tag.querySelector('text').setAttribute('y',yp(b[4])+4);tag.querySelector('text').textContent=fmt(b[4]);
      const extra = [state.indicators.has('sma20') && d.sma20!==null ? `MM20 ${safe(d.sma20)}` : '',
        state.indicators.has('sma50') && d.sma50!==null ? `MM50 ${safe(d.sma50)}` : '',
        ...['sma200','ema20','ema50'].map(key=>state.indicators.has(key)&&d[key]!==null?`${key.replace('sma','MM').replace('ema','EMA')} ${safe(d[key])}`:''),
        state.indicators.has('atr') && d.atr14_wilder!==null ? `ATR Wilder ${safe(d.atr14_wilder)} MAD` : '',
        state.indicators.has('rsi') && d.rsi!==null ? `RSI ${safe(d.rsi)}` : '',
        state.indicators.has('macd') && d.macd!==null ? `MACD ${safe(d.macd)}` : ''].filter(Boolean).join(' · ');
      const previous=bars[start+j-1]?.[4], delta=previous>0?(b[4]/previous-1)*100:null;
      readout.innerHTML = `<strong>${b[0]}</strong><span>Ouverture <b>${fmt(b[1])}</b></span><span>Haut <b>${fmt(b[2])}</b></span><span>Bas <b>${fmt(b[3])}</b></span><span>Clôture <b>${fmt(b[4])} MAD</b></span><span>Volume <b>${fmt(b[5])} titres</b></span>` +
        (delta===null?'':`<span class="${delta>=0?'gain':'loss'}">${delta>=0?'+':''}${fmt(delta)} % depuis la précédente séance disponible</span>`) +
        (extra?`<span class="chart-extra">${extra}</span>`:'');
      readout.setAttribute('aria-live', announce ? 'polite' : 'off');
    }
    selectBar=(index,announce=false)=>select(index-start,announce);
    select(state.selected !== null && state.selected >= start && state.selected < state.end ? state.selected-start : visible.length-1);
    explorer?.sync();
  }
  periodButtons.forEach(b => b.addEventListener('click', () => {
    const count=b.dataset.period==='all'?bars.length:Math.min(Number(b.dataset.period),bars.length);
    state.set(count,bars.length-count);state.period=b.dataset.period;explorer.resetCursor();render();
  }));
  toggleButtons.forEach(b => b.addEventListener('click', () => {
    const key=b.dataset.indicator;
    state.indicators.has(key)?state.indicators.delete(key):state.indicators.add(key);
    save();render();
  }));
  modeButtons.forEach(b => b.addEventListener('click', () => {state.type=b.dataset.chartType;save();render();}));
  root.querySelectorAll('[data-chart-preset]').forEach(b=>b.addEventListener('click',()=>{
    const preset=b.dataset.chartPreset;
    state.indicators=new Set(preset==='trend'?['volume','sma20','sma50']:preset==='momentum'?['volume','rsi','macd']:['volume']);
    save();render();
  }));
  root.querySelector('[data-chart-theme]')?.addEventListener('click',()=>{root.dataset.chartTheme=root.dataset.chartTheme==='light'?'dark':'light';save();render();});
  root.querySelectorAll('[data-chart-tool]').forEach(b=>b.addEventListener('click',()=>setTool(b.dataset.chartTool)));
  root.querySelector('[data-chart-undo]')?.addEventListener('click',()=>{drawings.pop();draft=null;save();render();});
  holder.addEventListener('keydown',e=>{if(e.key==='Escape'){setTool('cursor');render();}});
  root.querySelector('[data-chart-export]')?.addEventListener('click',()=>{
    const source=holder.querySelector('svg'),copy=source.cloneNode(true);
    const originals=[source,...source.querySelectorAll('*')],clones=[copy,...copy.querySelectorAll('*')];
    originals.forEach((node,i)=>{
      const style=getComputedStyle(node);
      for(const key of ['fill','stroke','stroke-width','stroke-dasharray','opacity','font-family','font-size','font-weight','background-color'])clones[i].style.setProperty(key,style.getPropertyValue(key));
    });
    copy.setAttribute('width',String(holder.clientWidth));copy.setAttribute('height',String(source.viewBox.baseVal.height));
    const description=document.createElementNS('http://www.w3.org/2000/svg','desc');
    description.textContent=`${symbol} · ${info.textContent} · Source : fiche Nour datée. Cours non ajustés. Les tracés sont personnels.`;
    copy.prepend(description);
    const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml'}));
    const a=document.createElement('a');a.href=url;a.download=`Nour-${symbol}-${bars.at(-1)[0]}.svg`;a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  explorer=window.NourCharts.mount({root,chart:holder,state,points:bars.map(b=>[b[0],b[4]]),
    defaultCount:Math.min(252,bars.length),onChange:render,onRead:(i,a)=>selectBar(i,a),onPick:(i,e)=>{
      if(tool==='cursor')return false;
      const point=e?pickPoint(i,e):[bars[i][0],bars[i][4]];if(!point)return true;
      if(tool==='level'){drawings.push({type:'level',points:[point]});setTool('cursor');}
      else if(!draft){draft=point;if(status)status.textContent='Premier point posé ; choisissez le second.';render();return true;}
      else{drawings.push({type:'trend',points:[draft,point]});setTool('cursor');}
      drawings=drawings.slice(-40);save();render();return true;
    }});
  if(!storageReady)setTool('cursor');
  render();
})();
