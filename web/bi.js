/* Read-only financial explanations. Values remain server-rendered from Nour. */
(()=>{'use strict';
  document.querySelectorAll('[data-bi-dashboard]').forEach(root=>{
    const cards=[...root.querySelectorAll('[data-bi-metric]')];
    const panels=[...root.querySelectorAll('[data-bi-explanation]')];
    const filter=root.querySelector('#bi-group');
    const status=root.querySelector('[data-bi-status]');
    function select(card){
      cards.forEach(c=>c.setAttribute('aria-pressed',String(c===card)));
      panels.forEach(p=>{
        const chosen=p.dataset.biExplanation===card.dataset.biMetric;
        p.hidden=!chosen;p.open=chosen;
      });
      status.textContent=card.querySelector('span').textContent+' · '+card.querySelector('strong').textContent+' '+card.querySelector('small').textContent;
    }
    root.classList.add('bi-enhanced');
    root.querySelector('[data-bi-filters]').hidden=false;
    cards.forEach(card=>card.addEventListener('click',()=>select(card)));
    filter.addEventListener('change',()=>{
      cards.forEach(c=>{c.hidden=filter.value!=='all'&&c.dataset.biGroup!==filter.value;});
      const selected=cards.find(c=>c.getAttribute('aria-pressed')==='true'&&!c.hidden)||cards.find(c=>!c.hidden);
      if(selected)select(selected);
    });
    select(cards.find(c=>c.getAttribute('aria-pressed')==='true')||cards[0]);
  });
})();
