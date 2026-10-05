(() => {
  'use strict';
  const q = selector => document.querySelector(selector);
  const search = q('#search'), sector = q('#sector'), marketBody = q('#market-body');
  const filterMarket = () => {
    const term = (search?.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    document.querySelectorAll('[data-market-row]').forEach(row => {
      row.hidden = !(row.dataset.search.includes(term) && (!sector?.value || row.dataset.sector === sector.value));
    });
  };
  search?.addEventListener('input', filterMarket);
  sector?.addEventListener('change', filterMarket);
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
})();
