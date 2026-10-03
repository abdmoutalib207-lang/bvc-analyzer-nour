"""Evidence-bound editorial layer, independent of score calculations."""
from math import isfinite
from .market_view import fmt


def numeric(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v)


def comparison(row, session, previous):
    values=row.get('close_series_last_60') or []; dates=row.get('close_dates_last_60') or []
    if (row.get('asof')==session and len(values)>=2 and len(values)==len(dates)
            and dates[-1]==session and dates[-2]==previous and numeric(values[-2]) and values[-2]>0):
        return round((values[-1]/values[-2]-1)*100,2)
    return None


CHECKPOINTS={
    'ADI':'Préventes, livraisons, stocks, dette et conversion du résultat en trésorerie.',
    'RDS':'Backlog sécurisé, reconnaissance du chiffre d’affaires, livraisons et trésorerie.',
    'TGCC':'Carnet de commandes, marges, BFR et conversion en cash.',
    'SGTM':'Carnet de commandes, prises de commandes, BFR et dette nette.',
    'CMGP':'Mix d’activité, marge, BFR et financement de la croissance.',
    'MSA':'Trafic portuaire, concessions, capacité, investissements et trésorerie.',
    'SMI':'Production, prix de l’argent, coûts, investissements et trésorerie.',
    'CMT':'Production, prix des métaux, coûts et événements liés à la reprise.',
    'T2S':'Mix équipements/services, marge, créances clients et trésorerie.',
}


def title_reading(row,session,previous,masi_change):
    t=row.get('technical') or {};p=row.get('price');day=comparison(row,session,previous)
    relative=round(day-masi_change,2) if day is not None and numeric(masi_change) else None
    result={'change_pct':day,'previous_session':previous if day is not None else None,
            'relative_masi_pp':relative,'paragraphs':[],'fundamental':row.get('fundamental') or {},
            'checkpoint':CHECKPOINTS.get(row['symbol'],'Résultats, bilan, trésorerie et indicateurs propres au secteur.'),
            'source':row.get('price_source'),'liquidity':row.get('liquidity') or {},
            'turnover_mad':row.get('day_turnover_mad_actual')}
    out=result['paragraphs']
    if row.get('asof')!=session or row.get('decision') in ('INDISPONIBLE','SUSPENDU'):
        out.append('Donnée absente, ancienne ou suspendue : aucune lecture de la séance courante n’est attribuée à ce titre.')
        return result
    if relative is not None:
        direction='surperforme' if relative>0 else 'sous-performe' if relative<0 else 'évolue comme'
        out.append(f'Le titre {direction} le MASI de {fmt(abs(relative))} point(s) sur la même séance. '+
                   ('Il progresse malgré la baisse de l’indice.' if day>0 and masi_change<0 else
                    'Cette comparaison mesure la résistance relative de la séance, pas une accumulation institutionnelle.'))
    else: out.append('Variation journalière comparable non disponible : aucun pourcentage n’est reconstruit depuis une séance plus ancienne.')
    if t.get('limited_by_resumption'):
        out.append('La reprise change le régime de comparaison. Les tendances et niveaux antérieurs restent écartés ; observer la fréquence des échanges et l’offre réellement disponible.')
    elif numeric(p):
        for relation,op in [('sous',lambda a,b:a<b),('au-dessus de',lambda a,b:a>=b)]:
            horizons=[str(n) for n in (20,50) if numeric(t.get(f'sma{n}')) and op(p,t[f'sma{n}'])]
            if horizons: out.append(f'Clôture {relation} la moyenne à {" et ".join(horizons)} séances : '+
                                    ('la structure reste fragile sur ces horizons.' if relation=='sous' else 'la tenue doit être confirmée lors des prochaines cotations.'))
        support,resistance=t.get('support20'),t.get('resistance20')
        if numeric(support) and numeric(resistance):
            if p<support: out.append(f'Le plancher des 20 séances précédentes, {fmt(support)} MAD, est rompu. Il devient un niveau de reconquête ; il n’est plus présenté comme un support qui tient. La borne haute de référence reste {fmt(resistance)} MAD.')
            elif p>resistance: out.append(f'La borne haute des 20 séances précédentes, {fmt(resistance)} MAD, est franchie. Surveiller sa tenue en clôture ; un retour sous ce niveau annulerait le franchissement observé.')
            else: out.append(f'Le cours reste entre le plancher {fmt(support)} et la borne haute {fmt(resistance)} MAD des 20 séances précédentes. Une rupture du plancher détériorerait la structure ; un dépassement de la borne haute nécessiterait une confirmation.')
        rsi=t.get('rsi14')
        if numeric(rsi): out.append(f'RSI 14 à {fmt(rsi)} : '+('momentum très faible ; une survente ne garantit pas un rebond.' if rsi<30 else 'momentum inférieur au seuil neutre de 50.' if rsi<50 else 'momentum au-dessus du seuil neutre de 50.' if rsi<=70 else 'momentum élevé ; surveiller le risque de retracement.'))
    ratio=t.get('volume_vs_median20')
    if numeric(ratio): out.append(f'Quantité échangée : {fmt(ratio)} fois la médiane des 20 séances précédentes. '+
                                 ('L’activité s’intensifie ; ' if ratio>=2 else '')+'le volume seul ne permet pas de distinguer absorption, distribution ou achats institutionnels.')
    liq=result['liquidity']
    if liq.get('ready') and numeric(liq.get('median_turnover_ex_top5_mad_estimated')):
        out.append(f'Liquidité robuste estimée hors cinq plus fortes séances : {fmt(liq["median_turnover_ex_top5_mad_estimated"]/1e6)} MDH, contre {fmt(liq["median_turnover_mad_estimated"]/1e6)} MDH de médiane. Montants estimés par clôture × quantité ; carnet et glissement non observés.')
    return result


def market_reading(report,overview,session):
    index=overview.get('masi') or {};current=index.get('value');change=index.get('change_pct')
    provisional=overview.get('status')!='closed'
    history=sorted((d,v) for d,v in (report.get('masi_history') or {}).items() if d<session and numeric(v) and v>0) if session else []
    prev=history[-1][0] if history else index.get('veille_asof')
    rows=[r for r in report['results'] if r.get('asof')==session and r.get('decision') not in ('INDISPONIBLE','SUSPENDU')]
    paragraphs=[];vigilance=[];scenarios=[];levels={}
    breadth=overview.get('breadth') or {};up,down,quoted=(breadth.get(k) for k in ('up','down','quoted'))
    if numeric(current) and numeric(change):
        paragraphs.append(f'Le MASI {"est observé" if provisional else "termine"} à {fmt(current)} points ({fmt(change)} %). '+
                          ('La séance demeure provisoire ; une observation intrajournalière ne valide pas une cassure en clôture.' if provisional else
                           'La direction de cette séance est baissière.' if change<0 else 'La direction de cette séance est haussière.' if change>0 else 'L’indice est stable sur cette séance.'))
    if all(numeric(v) for v in (up,down,quoted)) and quoted>0:
        paragraphs.append(f'{down} valeurs baissent, {up} progressent et {breadth.get("flat",0)} sont inchangées sur {quoted} traitées. Les baisses représentent {fmt(down/quoted*100)} % de cette couverture. '+
                          ('La faiblesse est largement partagée ; elle ne se limite pas à quelques grandes capitalisations.' if down/quoted>=.65 else 'La hausse est largement partagée.' if up/quoted>=.65 else 'La largeur de marché reste partagée.'))
    hi,lo=overview.get('high'),overview.get('low')
    if all(numeric(v) for v in (current,hi,lo)) and hi>lo and lo<=current<=hi:
        position=(current-lo)/(hi-lo)*100
        paragraphs.append(f'L’indice se situe à {fmt(position)} % de l’amplitude au-dessus du plus bas ({fmt(lo)}), pour un plus haut de {fmt(hi)} points. '+
                          ('Une clôture proche du bas de séance traduit une pression persistante jusqu’à la fin des échanges.' if position<=20 and not provisional else 'La position dans la fourchette décrit la séance ; elle ne prédit pas la suivante.'))
    amount=overview.get('turnover_mad')
    if numeric(amount): paragraphs.append(f'Le relevé de marché totalise {fmt(amount/1e6)} MDH. Aucune comparaison avec le volume de la veille n’est publiée sans un relevé de même périmètre ; une hausse des volumes n’est donc pas supposée.')
    if len(history)>=20 and numeric(current) and not provisional:
        past=history[-20:];support=min(v for _,v in past);resistance=max(v for _,v in past)
        levels={'support_close20':support,'resistance_close20':resistance,'since':past[0][0],'until':past[-1][0]}
        if current<support:
            paragraphs.append(f'L’indice passe sous le plus bas des 20 clôtures précédentes, {fmt(support)} points. Cette référence devient une zone à reconquérir. Il ne s’agit pas d’un support intrajournalier.')
            vigilance.append(f'MASI : reconquête de {fmt(support)} points, puis amélioration de la largeur. Aucun support inférieur n’est inventé depuis cet extrait.')
            scenarios=[{'name':'Poursuite baissière','condition':f'Maintien sous {fmt(support)} et nouveau plus bas lors d’une prochaine clôture.','reading':'La cassure reste dominante ; une nouvelle baisse étendrait la détérioration.'},
                       {'name':'Stabilisation','condition':'Absence de nouveau plus bas et réduction des valeurs en recul sur plusieurs séances.','reading':'Une base pourrait se construire ; une séance calme ne suffit pas à confirmer un retournement.'},
                       {'name':'Rebond et réparation','condition':f'Reconquête de {fmt(support)} en clôture avec une largeur améliorée.','reading':f'Le haut de l’intervalle historique reste {fmt(resistance)} ; aucune cible intermédiaire n’est postulée.'}]
        else:
            paragraphs.append(f'Les 20 clôtures précédentes dessinent un intervalle de référence {fmt(support)}–{fmt(resistance)} points. Ce sont des bornes observées, pas des objectifs de cours.')
            vigilance.append(f'MASI : tenue de {fmt(support)} ; franchissement confirmé de {fmt(resistance)} pour sortir de l’intervalle observé.')
            scenarios=[{'name':'Dégradation','condition':f'Clôture sous {fmt(support)} accompagnée d’une largeur négative.','reading':'La sortie par le bas invaliderait la tenue de l’intervalle.'},
                       {'name':'Consolidation','condition':f'Maintien entre {fmt(support)} et {fmt(resistance)}.','reading':'Surveiller la largeur et la persistance des échanges.'},
                       {'name':'Amélioration','condition':f'Clôture au-dessus de {fmt(resistance)} et hausse partagée.','reading':'Une sortie par le haut doit tenir lors des séances suivantes.'}]
    else: vigilance.append('Attendre une clôture confirmée et un historique suffisant avant de publier des scénarios chiffrés sur le MASI.')
    sectors=sorted([s for s in overview.get('sectors',[]) if numeric(s.get('variation_pct'))],key=lambda s:s['variation_pct'],reverse=True)
    sector_paragraphs=[]
    if sectors:
        sector_paragraphs.append(f'{sum(s["variation_pct"]<0 for s in sectors)} indices sectoriels reculent sur {len(sectors)} renseignés. Ces variations décrivent les prix, pas la qualité des résultats des entreprises.')
        for label,group in [('Secteurs les plus résistants',sectors[:3]),('Secteurs les plus faibles',list(reversed(sectors[-3:])) )]:
            sector_paragraphs.append(label+' : '+' ; '.join(f'{s["libelle"]} ({fmt(s["variation_pct"])} %)' for s in group)+'.')
    else: sector_paragraphs.append('Indices sectoriels non disponibles à la date considérée.')
    ranked=[]
    if not provisional:
        for row in rows:
            value=comparison(row,session,prev)
            if value is not None:ranked.append({'symbol':row['symbol'],'change_pct':value})
    ranked.sort(key=lambda r:r['change_pct'],reverse=True)
    flows=sorted([{'symbol':r['symbol'],'amount':r['day_turnover_mad_actual']} for r in rows if numeric(r.get('day_turnover_mad_actual')) and r['day_turnover_mad_actual']>0],key=lambda r:r['amount'],reverse=True)[:5]
    return {'paragraphs':paragraphs,'levels':levels,'previous_session':prev,'provisional':provisional,'sector_paragraphs':sector_paragraphs,'sectors':sectors,'leaders':ranked[:5],'laggards':list(reversed(ranked[-5:])),
            'ranking_coverage':len(ranked),'flows':flows,'scenarios':scenarios,'vigilance':vigilance,'source_url':overview.get('source_url'),'source':overview.get('source'),'observed_at':overview.get('observed_at')}
