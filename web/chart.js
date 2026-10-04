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
  const series = bars.map(() => ({sma20: null, sma50: null, upper: null, lower: null,
    rsi: null, macd: null, signal: null}));
  let closes = [], ema12 = null, ema26 = null, signal = null;
  let macds = [], avgGain = null, avgLoss = null;
  bars.forEach((b, i) => {
    if (b[0] < since) return; // Reset indicators after a documented resumption.
    const c = b[4], prev = closes.at(-1);
    closes.push(c);
    const n = closes.length;
    const mean = p => closes.slice(-p).reduce((sum, x) => sum + x, 0) / p;
    if (n >= 20) {
      const avg = mean(20);
      const variance = closes.slice(-20).reduce((sum, x) => sum + (x - avg) ** 2, 0) / 20;
      series[i].sma20 = avg;
      series[i].upper = avg + 2 * Math.sqrt(variance);
      series[i].lower = avg - 2 * Math.sqrt(variance);
    }
    if (n >= 50) series[i].sma50 = mean(50);
    if (n === 12) ema12 = mean(12);
    else if (n > 12) ema12 += (c - ema12) * 2 / 13;
    if (n === 26) ema26 = mean(26);
    else if (n > 26) ema26 += (c - ema26) * 2 / 27;
    if (ema12 !== null && ema26 !== null) {
      const macd = ema12 - ema26;
      series[i].macd = macd;
      macds.push(macd);
      if (macds.length === 9) signal = macds.reduce((sum, x) => sum + x, 0) / 9;
      else if (macds.length > 9) signal += (macd - signal) * 2 / 10;
      if (signal !== null) series[i].signal = signal;
    }
    if (n === 15) {
      const diffs = closes.slice(1).map((x, j) => x - closes[j]);
      avgGain = diffs.reduce((sum, x) => sum + Math.max(x, 0), 0) / 14;
      avgLoss = diffs.reduce((sum, x) => sum + Math.max(-x, 0), 0) / 14;
    } else if (n > 15) {
      const diff = c - prev;
      avgGain = (avgGain * 13 + Math.max(diff, 0)) / 14;
      avgLoss = (avgLoss * 13 + Math.max(-diff, 0)) / 14;
    }
    if (avgGain !== null) series[i].rsi = avgGain + avgLoss === 0 ? 50 :
      avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  });

  const state = Object.assign(new window.NourCharts.Viewport(bars.length, Math.min(252,bars.length)),
    {type:'line', period:'252', indicators:new Set(['volume']), selected:null});
  let explorer, selectBar = () => {};
  const periodButtons = [...root.querySelectorAll('[data-period]')];
  const toggleButtons = [...root.querySelectorAll('[data-indicator]')];
  const modeButtons = [...root.querySelectorAll('[data-chart-type]')];
  const updateButtons = () => {
    periodButtons.forEach(b => b.setAttribute('aria-pressed', String(state.period === b.dataset.period)));
    toggleButtons.forEach(b => b.setAttribute('aria-pressed', String(state.indicators.has(b.dataset.indicator))));
    modeButtons.forEach(b => b.setAttribute('aria-pressed', String(state.type === b.dataset.chartType)));
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
    const L = 57, R = W-65, plotW = R - L, top = 27, priceH = W>600 ? 290 : 228;
    holder.dataset.plotLeft=L; holder.dataset.plotRight=R;
    const volumeOn = state.indicators.has('volume');
    const volumeY = top + priceH + 20;
    const rsiY = volumeY + (volumeOn ? 65 : 5);
    const rsiOn = state.indicators.has('rsi');
    const macdY = rsiY + (rsiOn ? 101 : 0);
    const macdOn = state.indicators.has('macd');
    const height = macdY + (macdOn ? 103 : 0) + 25;
    const x = j => L + (j + .5) * plotW / visible.length;
    const priceValues = visible.flatMap(b => state.type === 'candles' ? [b[2], b[3]] : [b[4]]);
    if (state.indicators.has('sma20')) priceValues.push(...derived.map(d => d.sma20).filter(v => v !== null));
    if (state.indicators.has('sma50')) priceValues.push(...derived.map(d => d.sma50).filter(v => v !== null));
    if (state.indicators.has('bands')) priceValues.push(...derived.flatMap(d => [d.upper, d.lower]).filter(v => v !== null));
    let lo = Math.min(...priceValues), hi = Math.max(...priceValues);
    const pad = (hi - lo) * .08 || Math.max(hi * .01, .01);
    lo -= pad; hi += pad;
    const yp = v => top + priceH * (hi - v) / (hi - lo);
    const axes = [0,1,2,3,4].map(j => {
      const yy = top + priceH * j / 4;
      return `<line x1="${L}" x2="${R}" y1="${yy}" y2="${yy}" class="chart-grid"/><text x="3" y="${yy+4}">${fmt(hi-(hi-lo)*j/4)}</text>`;
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
    if (state.indicators.has('bands')) indicators += overlay('upper','#a18feb') + overlay('lower','#a18feb');
    if (state.indicators.has('sma20')) indicators += overlay('sma20','#f3ce77');
    if (state.indicators.has('sma50')) indicators += overlay('sma50','#5ac9de');
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
        `<path d="${path(derived.map(d=>d.rsi),x,yr)}" fill="none" stroke="#c9a3f1" stroke-width="1.8"/>`;
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
        `<path d="${path(derived.map(d=>d.macd),x,ym)}" fill="none" stroke="#83d6e5" stroke-width="1.8"/>` +
        `<path d="${path(derived.map(d=>d.signal),x,ym)}" fill="none" stroke="#f3ce77" stroke-width="1.5"/>`;
    }
    const comparison=explorer?.selection();
    const range = comparison ? comparison.map(i=>clamp(i-start,0,visible.length-1)).sort((a,b)=>a-b) : null;
    const highlight=range ? `<rect x="${x(range[0])}" y="${top}" width="${x(range[1])-x(range[0])}" height="${priceH}" fill="#f3ce77" opacity=".1"/>` : '';
    holder.innerHTML = `<svg viewBox="0 0 ${W} ${height}" role="img" aria-label="Graphique OHLCV de ${visible.length} séances">${axes}${highlight}${price}${indicators}<line class="chart-cross" x1="0" x2="0" y1="${top}" y2="${height-22}" visibility="hidden"/><line class="chart-cross-price" x1="${L}" x2="${R}" y1="0" y2="0" visibility="hidden"/><circle class="chart-point" cx="0" cy="0" r="4" visibility="hidden"/><g class="chart-price-tag" visibility="hidden"><rect x="${R+3}" y="0" width="60" height="20" rx="3"/><text x="${R+6}" y="0"></text></g><text x="${L}" y="${height-5}">${visible[0][0]}</text><text text-anchor="end" x="${R}" y="${height-5}">${visible.at(-1)[0]}</text></svg>`;
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
    render();
  }));
  modeButtons.forEach(b => b.addEventListener('click', () => {state.type=b.dataset.chartType;render();}));
  explorer=window.NourCharts.mount({root,chart:holder,state,points:bars.map(b=>[b[0],b[4]]),
    defaultCount:Math.min(252,bars.length),onChange:render,onRead:(i,a)=>selectBar(i,a)});
  render();
})();
