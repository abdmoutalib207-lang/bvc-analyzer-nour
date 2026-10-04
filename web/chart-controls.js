/* Shared viewport interactions. Only display state is changed, never observations. */
(() => {
  'use strict';
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  class Viewport {
    constructor(length, count) {
      this.length = length; this.minimum = Math.min(6, length);
      this.set(count, length - count);
    }
    get start() { return this.end - this.count; }
    set(count, start) {
      this.count = clamp(Math.round(count), this.minimum, this.length);
      this.end = clamp(Math.round(start), 0, this.length - this.count) + this.count;
    }
    zoom(factor, ratio = .5) {
      ratio = clamp(ratio, 0, 1);
      const anchor = this.start + ratio * this.count;
      const count = clamp(Math.round(this.count * factor), this.minimum, this.length);
      this.set(count, anchor - ratio * count);
    }
    pan(sessions) { this.set(this.count, this.start + sessions); }
  }

  function mount({root, chart, state, points, defaultCount, onChange, onRead}) {
    const overview = root.querySelector('[data-chart-overview]');
    const measure = root.querySelector('[data-chart-measure]');
    const help = root.querySelector('[data-chart-help]');
    const rangeStart = root.querySelector('[data-chart-range-start]');
    const rangeEnd = root.querySelector('[data-chart-range-end]');
    const fullscreen = root.querySelector('[data-chart-fullscreen]');
    const defaultPeriod = state.period;
    const number = v => new Intl.NumberFormat('fr-FR', {maximumFractionDigits:2}).format(v);
    let pending = 0, gesture = null, navigation = null, anchor = null, pinned = false;
    let comparing = false, compareStart = null, compareEnd = null;
    const pointers = new Map();
    const redraw = () => {
      if (!pending) pending = requestAnimationFrame(() => {pending = 0; onChange();});
    };
    const change = () => { state.period = null; redraw(); };
    const ratio = clientX => {
      const rect = chart.getBoundingClientRect();
      const left = Number(chart.dataset.plotLeft || 57), right = Number(chart.dataset.plotRight || rect.width-40);
      return clamp((clientX-rect.left-left)/(right-left), 0, 1);
    };
    const index = clientX => clamp(state.start + Math.floor(ratio(clientX)*state.count), state.start, state.end-1);
    const syncFullscreen = () => {
      const active=document.fullscreenElement===root || root.classList.contains('chart-expanded');
      fullscreen?.setAttribute('aria-pressed',String(active));
      if (fullscreen) fullscreen.textContent=active ? 'Quitter plein écran' : 'Plein écran';
      redraw();
    };
    document.addEventListener('fullscreenchange',syncFullscreen);
    function measurement() {
      if (!measure) return;
      measure.hidden = !comparing;
      if (!comparing) return;
      if (compareStart === null) {measure.textContent = 'Choisissez la première date sur le graphique.'; return;}
      if (compareEnd === null) {measure.textContent = `Départ ${points[compareStart][0]} · choisissez une deuxième date.`; return;}
      const a = points[Math.min(compareStart,compareEnd)], b = points[Math.max(compareStart,compareEnd)];
      const delta = b[1]-a[1], pct = a[1] > 0 ? 100*delta/a[1] : null;
      const unit = root.hasAttribute('data-masi-chart') ? 'points' : 'MAD';
      measure.textContent = `${a[0]} → ${b[0]} · ${number(a[1])} → ${number(b[1])} ${unit} · ${delta>=0?'+':''}${number(delta)} ${unit}` +
        (pct === null ? '' : ` (${pct>=0?'+':''}${number(pct)} %)`) + ' · Écart des clôtures historiques, hors dividendes et frais.';
    }
    function choose(i) {
      state.selected = i; pinned = true; onRead(i, true);
      if (comparing) {
        if (compareStart === null || compareEnd !== null) {compareStart = i; compareEnd = null;}
        else compareEnd = i;
        measurement(); redraw();
      }
    }
    function sync() {
      root.dataset.chartStart = String(state.start); root.dataset.chartEnd = String(state.end);
      root.querySelectorAll('[data-chart-nav]').forEach(b => {
        const cmd = b.dataset.chartNav;
        b.disabled = cmd === 'older' ? state.start === 0 : cmd === 'newer' || cmd === 'latest' ? state.end === state.length :
          cmd === 'zoom-in' ? state.count === state.minimum : cmd === 'zoom-out' ? state.count === state.length : false;
      });
      if (rangeStart && rangeEnd) {
        root.querySelector('[data-chart-range-controls]').hidden=false;
        rangeStart.min = '0'; rangeStart.max = String(state.end-state.minimum); rangeStart.value = String(state.start);
        rangeEnd.min = String(state.start+state.minimum); rangeEnd.max = String(state.length); rangeEnd.value = String(state.end);
        rangeStart.setAttribute('aria-valuetext',points[state.start][0]);
        rangeEnd.setAttribute('aria-valuetext',points[state.end-1][0]);
      }
      root.querySelector('[data-chart-compare]')?.setAttribute('aria-pressed',String(comparing));
      if (overview) {
        const ys = points.map(p=>p[1]), lo=Math.min(...ys), span=Math.max(.01,Math.max(...ys)-lo);
        const x=i=>5+890*i/Math.max(1,state.length-1), y=v=>49-36*(v-lo)/span;
        const line=points.map((p,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ');
        const a=5+890*state.start/state.length, b=5+890*state.end/state.length;
        overview.innerHTML = `<svg viewBox="0 0 900 62" aria-hidden="true"><path d="${line}" fill="none" stroke="#81a9a0" stroke-width="1.4"/><rect x="5" y="5" width="${a-5}" height="49" fill="#08121b" opacity=".7"/><rect x="${b}" y="5" width="${895-b}" height="49" fill="#08121b" opacity=".7"/><rect data-edge="window" x="${a}" y="5" width="${Math.max(2,b-a)}" height="49" class="navigator-window"/><rect data-edge="start" x="${a-9}" y="3" width="18" height="53" class="navigator-handle"/><rect data-edge="end" x="${b-9}" y="3" width="18" height="53" class="navigator-handle"/></svg>`;
      }
      measurement();
    }
    chart.addEventListener('wheel', e => {
      if (e.cancelable) e.preventDefault();
      pinned = false;
      const delta=clamp(e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?300:1),-100,100);
      if (e.shiftKey || Math.abs(e.deltaX)>Math.abs(e.deltaY)) state.pan(Math.sign(e.deltaX || delta)*Math.max(1,Math.round(state.count*.08)));
      else state.zoom(Math.exp(delta*.004),ratio(e.clientX));
      change();
    }, {passive:false});
    const distance = () => {
      const [a,b]=[...pointers.values()];
      return Math.max(1,Math.hypot(a.x-b.x,a.y-b.y));
    };
    chart.addEventListener('pointerdown', e => {
      if (e.button !== 0) return;
      pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      chart.setPointerCapture(e.pointerId);
      if (pointers.size===1) gesture={x:e.clientX,y:e.clientY,start:state.start,count:state.count,moved:false};
      if (pointers.size===2) {
        const values=[...pointers.values()], r=ratio((values[0].x+values[1].x)/2);
        anchor={distance:distance(),count:state.count,point:state.start+r*state.count,ratio:r};
        gesture.moved=true;
      }
    });
    chart.addEventListener('pointermove', e => {
      if (pointers.has(e.pointerId)) pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      if (pointers.size>=2 && anchor) {
        const count=clamp(Math.round(anchor.count*anchor.distance/distance()),state.minimum,state.length);
        state.set(count,anchor.point-anchor.ratio*count); pinned=false; change(); return;
      }
      if (gesture && pointers.has(e.pointerId)) {
        const dx=e.clientX-gesture.x, dy=e.clientY-gesture.y;
        if (Math.abs(dx)>5 && (e.pointerType!=='touch' || Math.abs(dx)>Math.abs(dy))) gesture.moved=true;
        if (gesture.moved) {
          if (e.cancelable) e.preventDefault();
          const rect=chart.getBoundingClientRect(), w=Number(chart.dataset.plotRight)-Number(chart.dataset.plotLeft);
          state.set(gesture.count,gesture.start-dx/Math.max(1,w || rect.width)*gesture.count);
          pinned=false; chart.classList.add('is-dragging'); change();
        }
      } else if (!pinned) onRead(index(e.clientX),false);
    });
    const finish = (e,cancelled=false) => {
      const tap=gesture && !gesture.moved && pointers.size===1 && !cancelled;
      pointers.delete(e.pointerId); anchor=null;
      if (tap) choose(index(e.clientX));
      if (!pointers.size) {gesture=null; chart.classList.remove('is-dragging');}
      else {
        const remaining=[...pointers.values()][0];
        gesture={x:remaining.x,y:remaining.y,start:state.start,count:state.count,moved:true};
      }
    };
    chart.addEventListener('pointerup',e=>finish(e));
    chart.addEventListener('pointercancel',e=>finish(e,true));
    chart.addEventListener('keydown', e => {
      const i=clamp(state.selected ?? state.end-1,state.start,state.end-1);
      if (['ArrowLeft','ArrowRight','Home','End'].includes(e.key) && !e.shiftKey) {
        e.preventDefault(); pinned=true;
        state.selected=e.key==='Home'?state.start:e.key==='End'?state.end-1:clamp(i+(e.key==='ArrowLeft'?-1:1),state.start,state.end-1);
        onRead(state.selected,true);
      } else if (e.key==='+' || e.key==='=' || e.key==='-') {
        e.preventDefault();state.zoom(e.key==='-'?1.3:1/1.3);change();
      } else if (e.shiftKey && ['ArrowLeft','ArrowRight'].includes(e.key)) {
        e.preventDefault();state.pan((e.key==='ArrowLeft'?-1:1)*Math.max(1,Math.round(state.count*.2)));change();
      } else if (e.key==='Enter' || e.key===' ') {e.preventDefault();choose(i);}
      else if (e.key==='Escape') {pinned=false;comparing=false;compareStart=compareEnd=null;root.classList.remove('chart-expanded');measurement();syncFullscreen();}
    });
    chart.addEventListener('focus',()=>onRead(clamp(state.selected ?? state.end-1,state.start,state.end-1),true));
    root.querySelectorAll('[data-chart-nav]').forEach(b=>b.addEventListener('click',()=>{
      const cmd=b.dataset.chartNav;
      if (cmd==='older' || cmd==='newer') state.pan((cmd==='older'?-1:1)*Math.max(1,Math.round(state.count*.5)));
      if (cmd==='zoom-in' || cmd==='zoom-out') state.zoom(cmd==='zoom-in'?1/1.4:1.4);
      if (cmd==='latest') state.set(state.count,state.length-state.count);
      if (cmd==='reset') {state.set(defaultCount,state.length-defaultCount);state.period=defaultPeriod;}
      pinned=false;state.selected=null;
      if (cmd!=='reset') state.period=null;
      redraw();
    }));
    root.querySelector('[data-chart-compare]')?.addEventListener('click',()=>{
      comparing=!comparing; compareStart=compareEnd=null; pinned=false; measurement();redraw();
    });
    root.querySelector('[data-chart-fullscreen]')?.addEventListener('click',async()=>{
      try {
        if (document.fullscreenElement===root) await document.exitFullscreen();
        else if (root.requestFullscreen) await root.requestFullscreen();
        else {root.classList.toggle('chart-expanded');redraw();}
      } catch {root.classList.toggle('chart-expanded');redraw();}
      syncFullscreen();
    });
    root.querySelector('[data-chart-help-toggle]')?.addEventListener('click', e=>{
      help.hidden=!help.hidden;e.currentTarget.setAttribute('aria-expanded',String(!help.hidden));
    });
    const navRatio=e=>{
      const rect=overview.getBoundingClientRect();return clamp((e.clientX-rect.left)/rect.width,0,1);
    };
    overview?.addEventListener('pointerdown',e=>{
      if (e.button!==0) return;
      overview.setPointerCapture(e.pointerId);
      const edge=e.target.closest('[data-edge]')?.dataset.edge || 'center';
      navigation={edge,x:navRatio(e),start:state.start,end:state.end};
      if (edge==='center') {state.set(state.count,navRatio(e)*state.length-state.count/2);change();}
    });
    overview?.addEventListener('pointermove',e=>{
      if (!navigation) return;
      const n=navigation, delta=Math.round((navRatio(e)-n.x)*state.length);
      if (n.edge==='window') state.set(n.end-n.start,n.start+delta);
      if (n.edge==='start') {const start=clamp(n.start+delta,0,n.end-state.minimum);state.set(n.end-start,start);}
      if (n.edge==='end') state.set(clamp(n.end+delta,n.start+state.minimum,state.length)-n.start,n.start);
      pinned=false;change();
    });
    overview?.addEventListener('pointerup',()=>navigation=null);
    overview?.addEventListener('pointercancel',()=>navigation=null);
    rangeStart?.addEventListener('input',()=>{const start=Number(rangeStart.value);state.set(state.end-start,start);change();});
    rangeEnd?.addEventListener('input',()=>{state.set(Number(rangeEnd.value)-state.start,state.start);change();});
    const observer = new ResizeObserver(redraw); observer.observe(chart);
    return {sync, selection:()=>comparing && compareStart!==null && compareEnd!==null ? [compareStart,compareEnd] : null,
      resetCursor:()=>{pinned=false;state.selected=null;}, comparing:()=>comparing};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports={Viewport};
  if (typeof window !== 'undefined') window.NourCharts={Viewport,mount};
})();
