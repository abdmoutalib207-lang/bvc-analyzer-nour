/* Contract checks against the real export and the laboratory's shared math. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const api=require('../web/assistant.js');
const domains=require('../web/assistant-domains.js');
const research=require('../web/research.js');
const data=JSON.parse(fs.readFileSync('web/assistant-data.json','utf8'));
const fmt=x=>typeof x==='number'?x.toLocaleString('fr-FR',{maximumFractionDigits:2}):'indisponible';
let checked=0;
function check(q,predicate,context='MASI',state={},facts=data){
  const r=api.localAnswer(q,facts,context,state);assert.ok(predicate(r),q+'\n'+r.text);checked++;return r;
}
const menu=check('Quelles fonctions peux-tu expliquer ?',r=>r.domain==='navigation');
assert.equal(data.knowledge.capabilities.length,16);
for(const capability of data.knowledge.capabilities)assert.ok(menu.text.includes(capability.label));
const cases=[
  ['Comment télécharger les données ADI ?','chart','CSV'],
  ['Nombre de hausses et baisses MASI','market','Hausses'],
  ['Comment zoomer et lire les bougies ?','chart','Graphique'],
  ['Quelle activité et variation sur 20 séances ADI ?','technical','Variation sur 20'],
  ['BPA JET','fundamentals','BPA :'],
  ['Comment est calculé le score ADI ?','score','couverture'],
  ['Statistiques ADI sur 5 séances et Wilson','statistics','Wilson 95'],
  ['Liquidité ADI','liquidity','capacité à 10'],
  ['Risques ADI face au MASI','risk','Corrélation MASI'],
  ['Compare ADI aux titres du même secteur','sector','autres pairs'],
  ['Laboratoire ADI sur 20 séances','laboratory','médiane nette'],
  ['Actualités officielles JET','news','publication(s)'],
  ['Quel prix du Brent ?','macro','Brent'],
  ['Résume le briefing de clôture','briefing','séance de référence'],
  ['Quand a lieu la collecte ?','quality','09:45'],
  ['À quoi sert ECC et y a-t-il une IA générative ?','assistant','ECC'],
];
for(const [q,domain,term] of cases)check(q,r=>r.domain===domain&&r.text.toLowerCase().includes(term.toLowerCase())&&r.sources.length>0);
for(const [s,row] of Object.entries(data.symbols)){
  for(const [q,domain,term] of [['Risques','risk','Bêta : '+fmt(row.market_risk?.beta)],['Liquidité','liquidity','Scénario publié : '+fmt(row.liquidity?.scenario_shares)],['Comparables','sector','Secteur '+(row.sector_comparison?.sector||'indisponible')]]){
    check(q+' '+s,r=>r.domain===domain&&r.text.includes(term)&&r.sources.some(x=>x.url===row.url));
  }
}
for(const s of ['MASI','ADI','JET','CMT'])for(const horizon of [5,20,60])for(const period of ['all','2023-2024','2025+'])for(const regime of ['all','above','below']){
  const periodText=period==='all'?'toutes les périodes':period==='2025+'?'depuis 2025':'2023-2024';
  const regimeText=regime==='all'?'tous les régimes':regime==='above'?'au-dessus de MM200':'sous MM200';
  const selected=research.select(data.research.rows,{symbol:s,horizon,period,regime});
  const expected=research.summary(selected,.5,1.2,.1);
  check(`Laboratoire ${s} ${horizon} séances ${periodText} ${regimeText} achat 0,5 %, vente 1,2 %, glissement 0,1 %`,r=>r.domain==='laboratory'&&r.text.includes(expected.count+' observations')&&r.text.includes('médiane nette '+fmt(expected.median))&&r.text.includes('fréquence positive '+fmt(expected.positive))&&r.labFilters.period===period&&r.labFilters.regime===regime);
}
let previous=check('Laboratoire ADI sur 5 séances depuis 2025 achat 0,5 % vente 1,2 %',r=>r.labFilters.horizon===5&&r.labFilters.buy===.5&&r.labFilters.sell===1.2);
previous=check('Et sur 20 séances ?',r=>r.labFilters.horizon===20&&r.labFilters.period==='2025+'&&r.labFilters.buy===.5&&r.labFilters.sell===1.2,'ADI',previous);
check('Et avec glissement 0,2 % ?',r=>r.labFilters.slip===.2&&r.labFilters.horizon===20,'ADI',previous);
for(const q of ['Laboratoire ADI achat -1 %','Laboratoire ADI vente 11 %','Laboratoire ADI frais 2 %','Laboratoire ADI achat 1 % frais 2 %','Laboratoire ADI 10 séances','Laboratoire ADI en 2024'])check(q,r=>!r.labFilters&&!r.text.includes('médiane nette'));
check('Laboratoire ADI sans frais',r=>r.labFilters.buy===0&&r.labFilters.sell===0&&r.labFilters.slip===0);
check('Laboratoire ADI après franchissement du support demain',r=>r.text.includes('n’est pas implémenté')&&!r.labFilters);
check('Historique du score ADI',r=>r.text.includes('Archive prospective')&&r.text.includes('aucune efficacité prospective'));
const jet=data.symbols.JET.fundamental.latest_report;
check('Résultat total JET S1 2026',r=>r.text.includes('Résultat net consolidé total : '+fmt(jet.reported_total_net_millions)));
check('Résultat minoritaires JET S1 2026',r=>r.text.includes('Résultat des minoritaires : '+fmt(jet.reported_minority_net_millions)));
check('RNPG JET S1 2026',r=>r.text.includes('Résultat net part du groupe : '+fmt(jet.reported_net_millions)));
check('Résultat total JET S1 2025',r=>r.text.includes('Résultat net consolidé total : indisponible'));
check('Résultat total JET 2025',r=>r.text.includes('Résultat annuel total demandé : indisponible'));
check('RNPG M2M S1 2026',r=>r.text.includes('part du groupe de ce semestre : indisponible')&&r.text.includes('total (minoritaires compris)'));
check('RNPG ADI S1 2026',r=>r.text.includes('part du groupe : '+fmt(data.symbols.ADI.fundamental.latest_report.reported_net_millions)));
check('PER JET S1 2026',r=>r.text.includes('PER : indisponible')&&r.text.includes('ratio semestriel'));
check('Valeur comptable par action ADI',r=>r.text.includes('Valeur comptable par action : '+fmt(data.symbols.ADI.fundamental.book_value_per_share_mad)));
check('PNB ATW S1 2026',r=>r.text.includes('PNB semestriel : '+fmt(data.symbols.ATW.fundamental.latest_report.revenue_millions)));
check('CA ATW S1 2026',r=>r.text.includes('Chiffre d’affaires semestriel : indisponible'));
check('CA MGL S1 2026',r=>r.text.includes('Chiffre d’affaires semestriel : indisponible')&&r.text.includes('Montant d’activité semestrielle importé'));
check('CA JET S1 2025 et 2026',r=>r.text.includes('Chiffre d’affaires semestriel : '+fmt(jet.revenue_previous_millions))&&r.text.includes('période 2025-06-30')&&r.text.includes('Chiffre d’affaires semestriel : '+fmt(jet.revenue_millions)));
check('Source du Brent',r=>r.text.includes('Brent')&&r.sources.some(s=>s.label.includes('Brent')),'ADI');
check('Combien de valeurs montent et baissent ?',r=>r.text.includes('Hausses '+data.market.breadth.up),'ADI');
check('Quelle différence entre total et part groupe ?',r=>r.text.includes('RNPG signifie')&&!r.text.includes('ne reconnais'),'ADI');
check('Bandes Bollinger ADI',r=>r.text.includes('ne sont pas présentes dans cet export'));
check('Capitaux propres totaux CASH',r=>r.text.includes('totaux demandés : indisponible'));
for(const q of ['RSI ADI le 31/03/2026','Bêta ADI face au MASI le 31/03/2026','Laboratoire MASI le 31/03/2026'])check(q,r=>r.text.includes('n’est pas reconstruite aux dates demandées')&&!r.text.includes('Bêta :'));
check('RSI 7 ADI',r=>r.text.includes('n’est pas implémentée'));
check('PER ZZZ',r=>r.text.includes('non reconnu'));
check('Cours ADI le 31/02/2026',r=>r.text.includes('Date invalide'));
check('Briefing du 01/01/2023',r=>r.text.includes('n’est pas disponible'));
check('Briefing ADI',r=>r.text.includes('ADI')&&r.sources.some(x=>x.url==='briefing.html'));
check('Couverture des fondamentaux',r=>r.text.includes('références annuelles 77')&&r.text.includes('DIS, DLM, IBM'));
check('Cours provisoire ADI',r=>r.text.includes('Aucune cotation provisoire fraîche'));
const fixture=structuredClone(data);
fixture.news=[{title:'JET communiqué',publisher:'AMMC',published_at:'2026-10-06T10:00:00Z',tickers:['JET'],tier:'S1',url:'https://www.ammc.ma/test'},{title:'ADI presse',published_at:'2026-10-06T09:00:00Z',tickers:['ADI'],tier:'S2',url:'https://example.test/'},{title:'Fed annonce',published_at:'2026-10-05T09:00:00Z',tickers:[],tier:'S1',feed_id:'fed',url:'https://www.federalreserve.gov/'}];
check('Actualités officielles JET le 06/10/2026',r=>r.text.includes('JET communiqué')&&!r.text.includes('ADI presse'),'MASI',{},fixture);
check('Actualités Fed',r=>r.text.includes('Fed annonce')&&!r.text.includes('JET communiqué'),'ADI',{},fixture);
check('Actualités JET le 01/01/2023',r=>r.text.includes('ne signifie pas qu’aucune publication existe'),'MASI',{},fixture);
fixture.intraday.status='provisional';fixture.symbols.ADI.intraday_quote={price:336,shares:123,turnover_mad:41328};
check('Cours provisoire ADI',r=>r.text.includes('Cours provisoire 336 MAD'),'MASI',{},fixture);
fixture.intraday.status='stale';check('Cours provisoire ADI',r=>!r.text.includes('Cours provisoire 336 MAD'),'MASI',{},fixture);
fixture.symbols.ADI.fundamental.pe=null;check('PER ADI',r=>r.text.includes('PER : indisponible'),'MASI',{},fixture);
const csv=fs.readFileSync('web/historique/ADI.csv','utf8');
fixture.symbols.ADI.history_by_date=api.parseHistory(csv,'ADI',data.analysis_date);
const date=Object.keys(fixture.symbols.ADI.history_by_date).sort()[0],bar=fixture.symbols.ADI.history_by_date[date];
check('Bougie ADI le '+date,r=>r.text.includes('Clôture du '+date+' : '+fmt(bar.c))&&r.text.includes('Ouverture '+fmt(bar.o))&&r.sources.some(x=>x.url==='historique/ADI.csv'),'MASI',{},fixture);
const header=csv.replace(/^\uFEFF/,'').split(/\r?\n/)[0];
const row='2026-01-01;ADI;10;11;9;10;100;';
assert.throws(()=>api.parseHistory(header+'\n'+row+'\n'+row,'ADI',data.analysis_date),/dupliquées/);
assert.throws(()=>api.parseHistory('bad header','ADI',data.analysis_date),/Format/);
assert.equal(Object.keys(api.parseHistory(header+'\n2999-01-01;ADI;10;11;9;10;100;\n2026-02-30;ADI;10;11;9;10;100;\n2026-01-01;ADI;10;8;9;10;100;','ADI',data.analysis_date)).length,0);
assert.ok(!api.validURL('historique/../../private.csv'));
assert.ok(domains.labFilters('laboratoire 20 seances 1 % a l’achat 2 % a la vente').filters.buy===1);
console.log(`Assistant domains: ${checked} checked answers across all 16 capabilities, 108 lab filter/cost combinations, financial scopes, dated publications, full CSV history and follow-ups passed.`);
