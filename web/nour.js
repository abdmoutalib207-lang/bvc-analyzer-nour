(() => {
  'use strict';
  const q = selector => document.querySelector(selector);
  const issuerLinks=[...document.querySelectorAll('.issuer-nav a')];
  if(issuerLinks.length && 'IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{
      const current=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
      if(current)issuerLinks.forEach(link=>link.setAttribute('aria-current',String(link.hash==='#'+current.target.id)));
    },{rootMargin:'-70px 0px -60% 0px',threshold:0});
    issuerLinks.forEach(link=>{const section=q(link.hash);if(section)observer.observe(section);});
  }
  const search = q('#search'), sector = q('#sector'), marketBody = q('#market-body');
  const filterMarket = () => {
    const term = (search?.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    document.querySelectorAll('[data-market-row]').forEach(row => {
      row.hidden = !(row.dataset.search.includes(term) && (!sector?.value || row.dataset.sector === sector.value));
    });
  };
  search?.addEventListener('input', filterMarket);
  sector?.addEventListener('change', filterMarket);
  const filterFundamentals=()=>{
    const term=(q('#fundamental-search')?.value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const selected=q('#fundamental-sector')?.value||'',available=q('#fundamental-availability')?.value||'';
    const max=q('#fundamental-pe-max')?.value||'',min=q('#fundamental-roe-min')?.value||'';
    let visible=0;
    document.querySelectorAll('[data-fundamental-row]').forEach(row=>{
      const f=JSON.parse(row.dataset.facts);
      const coverage=!available||(available==='missing_eps'?f.eps_mad===null:available==='missing_annual'?!f.annual_exercise:Number.isFinite(f[available]));
      row.hidden=!(row.dataset.search.includes(term)&&(!selected||f.sector===selected)&&coverage&&
        (!max||(Number.isFinite(f.pe)&&f.pe<=Number(max)))&&(!min||(Number.isFinite(f.roe_pct)&&f.roe_pct>=Number(min))));
      if(!row.hidden)visible++;
    });
    if(q('#fundamental-count'))q('#fundamental-count').textContent=`${visible} titres affichés`;
  };
  for(const id of ['fundamental-search','fundamental-sector','fundamental-availability','fundamental-pe-max','fundamental-roe-min'])q('#'+id)?.addEventListener('input',filterFundamentals);
  q('#fundamental-reset')?.addEventListener('click',()=>{
    for(const id of ['fundamental-search','fundamental-sector','fundamental-availability','fundamental-pe-max','fundamental-roe-min'])if(q('#'+id))q('#'+id).value='';
    filterFundamentals();
  });
  q('#sort-score')?.addEventListener('click', () => {
    const rows = [...marketBody.querySelectorAll('[data-market-row]')];
    const descending = marketBody.dataset.sort !== 'desc';
    rows.sort((a,b) => descending ? Number(b.dataset.score)-Number(a.dataset.score)
      : Number(a.dataset.score)-Number(b.dataset.score));
    rows.forEach(row => marketBody.append(row));
    marketBody.dataset.sort = descending ? 'desc' : 'asc';
    q('#sort-score').textContent = descending ? 'Score : décroissant' : 'Score : croissant';
  });
  const filterNews = () => {
    const term = (q('#news-search')?.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const tier = q('#news-tier')?.value || '';
    const scope = q('#news-scope')?.value || '';
    const category = q('#news-category')?.value || '';
    let visible = 0;
    document.querySelectorAll('[data-news-row]').forEach(row => {
      const normalized = row.dataset.search.normalize('NFD').replace(/[\u0300-\u036f]/g,'');
      row.hidden = !(normalized.includes(term) && (!tier || row.dataset.tier === tier)
        && (!scope || row.dataset.scope === scope) && (!category || row.dataset.category === category));
      if (!row.hidden) visible++;
    });
    if (q('#news-count')) q('#news-count').textContent = `${visible} liens affichés`;
  };
  q('#news-search')?.addEventListener('input',filterNews);
  q('#news-tier')?.addEventListener('change',filterNews);
  q('#news-scope')?.addEventListener('change',filterNews);
  q('#news-category')?.addEventListener('change',filterNews);
  q('#news-reset')?.addEventListener('click',() => {
    ['#news-search','#news-tier','#news-scope','#news-category'].forEach(id => {if (q(id)) q(id).value='';});
    filterNews();
  });
  filterNews();
  const publication=q('[data-publication-commit]');
  if(publication&&/^[a-f0-9]{40}$/.test(publication.dataset.generator||'')){
    fetch('publication.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(manifest=>{
      if(manifest.generator_commit!==publication.dataset.generator||manifest.market_snapshot_sha256!==publication.dataset.marketHash||!/^[a-f0-9]{40}$/.test(manifest.publication_commit))throw new Error();
      publication.textContent=manifest.publication_commit;
    }).catch(()=>{publication.textContent='manifeste absent ou d’une autre construction ; identité non confirmée';});
  }
})();

document.addEventListener?.("error",function(e){if(e.target instanceof HTMLImageElement&&e.target.closest(".company-logo"))e.target.closest(".company-logo").classList.add("is-missing");},true);
