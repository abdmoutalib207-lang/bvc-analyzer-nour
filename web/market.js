/* MASI explorer uses real closes only: no invented OHLC or intraday trajectory. */
(() => {
  'use strict';
  const root=document.querySelector('[data-masi-chart]');
  if (!root) return;
  const all=JSON.parse(root.querySelector('#masi-data').textContent).filter(p=>
    Array.isArray(p) && /^\d{4}-\d{2}-\d{2}$/.test(p[0]) && Number.isFinite(p[1]) && p[1]>0);
  if (!all.length) return;
  const chart=root.querySelector('.masi-chart'),readout=root.querySelector('.chart-readout');
  const format=v=>new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(v);
  const tickDate=(date,width)=>width<450?`${date.slice(8)}/${date.slice(5,7)}/${date.slice(2,4)}`:date;
  const state=Object.assign(new window.NourCharts.Viewport(all.length,all.length),{selected:null,period:'0'});
  let explorer,selectPoint=()=>{};
  function render() {
    const series=all.slice(state.start,state.end),W=Math.max(240,Math.round(chart.clientWidth||900));
    const L=64,R=W-68,T=26,H=240;
    chart.dataset.plotLeft=L;chart.dataset.plotRight=R;
    const values=series.map(p=>p[1]),min=Math.min(...values),max=Math.max(...values),pad=Math.max((max-min)*.1,1);
    const low=min-pad,high=max+pad;
    const x=i=>L+(i+.5)*(R-L)/series.length,y=v=>T+H*(high-v)/(high-low);
    const line=series.map((p,i)=>`${i?'L':'M'}${x(i)},${y(p[1])}`).join(' ');
    const axes=Array.from({length:5},(_,i)=>`<line class="chart-grid" x1="${L}" x2="${R}" y1="${T+H*i/4}" y2="${T+H*i/4}"/><text x="2" y="${T+H*i/4+4}">${format(high-(high-low)*i/4)}</text>`).join('');
    const compare=explorer?.selection();
    const bounds=compare?.map(i=>Math.max(0,Math.min(series.length-1,i-state.start))).sort((a,b)=>a-b);
    const highlight=bounds?`<rect x="${x(bounds[0])}" y="${T}" width="${x(bounds[1])-x(bounds[0])}" height="${H}" fill="#f3ce77" opacity=".12"/>`:'';
    chart.innerHTML=`<svg viewBox="0 0 ${W} 300" role="img" aria-label="MASI, ${series.length} clôtures historiques">${axes}${highlight}<path d="${line} L${x(series.length-1)},${T+H} L${x(0)},${T+H} Z" fill="#b4e283" opacity=".06"/><path class="price-line" d="${line}"/><line class="chart-cross" x1="0" x2="0" y1="${T}" y2="${T+H}"/><line class="chart-cross-price" x1="${L}" x2="${R}" y1="0" y2="0"/><circle class="chart-point" cx="0" cy="0" r="4"/><text x="${L}" y="290">${tickDate(series[0][0],W)}</text><text x="${R}" text-anchor="end" y="290">${tickDate(series.at(-1)[0],W)}</text></svg>`;
    const cross=chart.querySelector('.chart-cross'),horizontal=chart.querySelector('.chart-cross-price'),dot=chart.querySelector('.chart-point');
    selectPoint=(index,announce=false)=>{
      const j=Math.max(0,Math.min(series.length-1,index-state.start));state.selected=state.start+j;
      const [date,value]=series[j],previous=all[state.selected-1]?.[1],change=previous>0?(value/previous-1)*100:null;
      cross.setAttribute('x1',x(j));cross.setAttribute('x2',x(j));
      horizontal.setAttribute('y1',y(value));horizontal.setAttribute('y2',y(value));
      dot.setAttribute('cx',x(j));dot.setAttribute('cy',y(value));
      readout.setAttribute('aria-live',announce?'polite':'off');
      readout.innerHTML=`<strong>${date}</strong><span>MASI <b>${format(value)} points</b></span>`+
        (change===null?'':`<span class="${change>=0?'gain':'loss'}">${change>=0?'+':''}${format(change)} % depuis la précédente séance disponible</span>`)+
        `<span class="chart-extra">Fenêtre ${series[0][0]} → ${series.at(-1)[0]} · ${series.length} séances</span>`;
    };
    selectPoint(state.selected!==null && state.selected>=state.start && state.selected<state.end?state.selected:state.end-1);
    root.querySelectorAll('[data-masi-period]').forEach(b=>b.setAttribute('aria-pressed',String(state.period===b.dataset.masiPeriod)));
    explorer?.sync();
  }
  root.querySelectorAll('[data-masi-period]').forEach(b=>b.addEventListener('click',()=>{
    const count=Number(b.dataset.masiPeriod)||all.length;
    state.set(count,all.length-count);state.period=b.dataset.masiPeriod;explorer.resetCursor();render();
  }));
  explorer=window.NourCharts.mount({root,chart,state,points:all,defaultCount:all.length,onChange:render,onRead:(i,a)=>selectPoint(i,a)});
  render();
})();
