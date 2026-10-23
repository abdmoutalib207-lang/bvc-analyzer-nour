(()=>{'use strict';
const controls=[...document.querySelectorAll('[data-anomaly-filter]')];
if(!controls.length)return;
const rows=[...document.querySelectorAll('[data-anomaly-row]')];
function apply(){let count=0;for(const row of rows){row.hidden=!controls.every(c=>!c.value||row.dataset[c.dataset.anomalyFilter]===c.value);if(!row.hidden)count++;}
const result=document.querySelector('[data-anomaly-count]');if(result)result.textContent=count+' anomalie(s) affichée(s)';}
controls.forEach(c=>c.addEventListener('change',apply));apply();
})();
