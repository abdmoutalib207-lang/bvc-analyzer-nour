"""Readable existing disclosures; display confidence never grants calculation rights."""
from copy import deepcopy
from datetime import date
import math
import re
from urllib.parse import urlsplit
from .financial_audit import REVIEWED

LABELS = {
 'resultat_net_part_groupe':'Résultat net part du groupe', 'resultat_net_consolide':'Résultat net consolidé total',
 'capitaux_propres_part_groupe':'Capitaux propres part du groupe', 'capitaux_propres_consolides':'Capitaux propres totaux publiés',
 'chiffre_affaires':'Chiffre d’affaires', 'produit_net_bancaire':'Produit net bancaire',
 'flux_tresorerie_exploitation':'Flux de trésorerie d’exploitation', 'endettement_net':'Endettement net publié',
 'dettes_financieres':'Dettes financières', 'tresorerie_actif':'Trésorerie à l’actif',
 'capex_decaisse':'CAPEX — montant du relevé',
}


def number(v):
    return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)


def source_url(v):
    if not isinstance(v,str):return None
    try:
        p=urlsplit(v)
        return v if p.scheme=='https' and p.hostname and not p.username and not p.password else None
    except ValueError:return None


def reported_facts(facts, asof):
    """Read stored facts verbatim; retain original units, doubts and disagreements."""
    f=facts or {}; rows=[]
    period=f.get('exercice_clos') or (str(f['exercice'])+'-12-31' if isinstance(f.get('exercice'),int) else None)
    for origin in ('faits','sector_faits'):
        for key,raw in (f.get(origin) or {}).items():
            if key.startswith('_') or not isinstance(raw,dict) or not number(raw.get('valeur')):continue
            url=source_url(raw.get('url') or f.get('url'))
            if not url:continue
            actual=raw.get('period_end')
            if actual:
                try:
                    if date.fromisoformat(actual)>date.fromisoformat(asof):continue
                except ValueError:continue
            original=number(raw.get('valeur_au_rapport')) and bool(raw.get('unite_au_rapport'))
            value=raw['valeur_au_rapport'] if original else raw['valeur']
            unit=raw.get('unite_au_rapport') if original else raw.get('unite')
            base=raw.get('base') or f.get('accounting_basis') or 'Périmètre à préciser'
            label=LABELS.get(key,key.replace('_',' ').capitalize())
            if 'social' in str(base).lower():
                if key=='resultat_net_part_groupe':label='Résultat net social (périmètre du relevé)'
                if key.startswith('capitaux_propres'):label='Capitaux propres sociaux (périmètre du relevé)'
            reviewed=(raw.get('validation_status') in REVIEWED and unit and actual and raw.get('base')
                and isinstance(raw.get('page'),int) and not isinstance(raw.get('page'),bool) and raw['page']>0
                and re.fullmatch('sha256:[0-9a-f]{64}',str(raw.get('document_hash',''))))
            rows.append(dict(id=origin+'-'+key,label=label,value=value,unit=unit or 'unité à préciser',
                period_end=actual,period_context=period,period_status='documented' if actual else 'dossier_only',
                scope=base,currency=raw.get('devise') or f.get('devise'),
                source=dict(url=url,page=raw.get('page'),title=f.get('document'),document_hash=raw.get('document_hash')),
                status='page_checked' if reviewed else 'referenced_to_review',
                notice=None if reviewed else 'Relevé existant à confirmer : consulter la pièce et ses réserves. Ne vaut pas validation pour un ratio.',
                note=raw.get('note') or '', original_amount_used=bool(original),
                stored_value=raw['valeur'],stored_unit=raw.get('unite'),used_for_score=False))
    latest=f.get('latest_report') or {};url=source_url(latest.get('document_url'))
    end=latest.get('period_end')
    if url and isinstance(end,str) and end<=asof:
        for field,label in [('reported_net_millions','Résultat net publié — voir périmètre'),('revenue_millions',
            'PNB publié' if f.get('semester_activity_label')=='PNB' else 'Activité publiée — voir nature dans la pièce')]:
            if not number(latest.get(field)):continue
            currency=latest.get('currency')
            unit={'MAD':'MDH','TND':'millions de TND'}.get(currency,'millions — devise à préciser')
            rows.append(dict(id='latest-'+field,label=label,value=latest[field],unit=unit,period_end=end,
                period_context=end,period_status='documented',scope=latest.get('accounting_basis') or 'Périmètre à préciser',
                currency=currency,source=dict(url=url,page=None,page_hint=latest.get('pages'),title='Dernière publication référencée'),
                status='referenced_to_review',notice='Publication référencée ; niveau de revue et périmètre à lire. Semestre non annualisé.',
                note=latest.get('note') or '',used_for_score=False))
    reservations=deepcopy(f.get('reservations') or [])
    conclusion=(f.get('financial_review') or {}).get('conclusion')
    if conclusion:reservations.append(conclusion)
    return dict(version='nour-reported-facts-v1',records=rows,
        reservations=reservations,
        notice='Chiffres déjà conservés dans Nour. Une référence affichée ne constitue pas une nouvelle revue du PDF. Les ratios gardent leurs contrôles propres.',
        used_for_score=False)
