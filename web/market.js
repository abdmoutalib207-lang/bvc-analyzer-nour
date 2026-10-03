(() => {
  'use strict';
  const root = document.querySelector('[data-masi-chart]');
  if (!root) return;
  const all = JSON.parse(root.querySelector('#masi-data').textContent);
  const chart = root.querySelector('.masi-chart');
  const readout = root.querySelector('.chart-readout');
  const format = value => new Intl.NumberFormat('fr-MA', {maximumFractionDigits: 2, minimumFractionDigits: 2}).format(value);
  const ns = 'http://www.w3.org/2000/svg';
  let series = all.slice(-63), selected = series.length - 1, cross, dot, svg;
  let low, high;
  function element(tag, attrs, text) {
    const e = document.createElementNS(ns, tag);
    for (const [key,value] of Object.entries(attrs)) e.setAttribute(key, value);
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function point(i) {
    return [65 + 810 * i / Math.max(1, series.length - 1), 260 - 230 * (series[i][1] - low) / (high - low)];
  }
  function select(i) {
    selected = Math.max(0, Math.min(series.length-1, i));
    const [x,y] = point(selected), [day,value] = series[selected];
    cross.setAttribute('x1',x); cross.setAttribute('x2',x);
    dot.setAttribute('cx',x); dot.setAttribute('cy',y);
    cross.hidden = false; dot.hidden = false;
    readout.textContent = `${day} · MASI ${format(value)} points`;
  }
  function render() {
    if (!series.length) return;
    const values = series.map(p=>p[1]);
    const min = Math.min(...values), max = Math.max(...values), pad = Math.max((max-min)*.12,1);
    low=min-pad; high=max+pad;
    svg = element('svg', {viewBox:'0 0 900 300', tabindex:'0', role:'img',
      'aria-label':`MASI, ${series.length} clôtures ; flèches gauche et droite pour parcourir`});
    for (let i=0;i<5;i++) {
      const y=30+i*57.5;
      svg.append(element('line',{x1:65,x2:875,y1:y,y2:y,stroke:'#29454c'}),
        element('text',{x:2,y:y+4},format(high-(high-low)*i/4)));
    }
    const points=series.map((_,i)=>point(i).join(',')).join(' ');
    svg.append(element('polygon',{points:`65,260 ${points} 875,260`,fill:'#b4e283',opacity:'.07'}),
      element('polyline',{points,fill:'none',stroke:'#b4e283','stroke-width':2.5}),
      element('text',{x:65,y:288},series[0][0]),
      element('text',{x:783,y:288},series.at(-1)[0]));
    cross=element('line',{x1:0,x2:0,y1:30,y2:260,stroke:'#9aafb6','stroke-dasharray':'4 4'});
    dot=element('circle',{cx:0,cy:0,r:4,fill:'#f3ce77',stroke:'#10212b','stroke-width':2});
    svg.append(cross,dot);
    svg.addEventListener('pointermove', e=>{
      const rect=svg.getBoundingClientRect(), x=(e.clientX-rect.left)/rect.width*900;
      select(Math.round((x-65)/810*(series.length-1)));
    });
    svg.addEventListener('pointerleave',()=>select(series.length-1));
    svg.addEventListener('keydown',e=>{
      if (['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) {
        e.preventDefault();
        select(e.key==='Home'?0:e.key==='End'?series.length-1:selected+(e.key==='ArrowRight'?1:-1));
      }
    });
    chart.replaceChildren(svg); select(series.length-1);
  }
  root.querySelectorAll('[data-masi-period]').forEach(button=>button.addEventListener('click',()=>{
    const n=Number(button.dataset.masiPeriod); series=n?all.slice(-n):all;
    root.querySelectorAll('[data-masi-period]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    render();
  }));
  render();
})();
