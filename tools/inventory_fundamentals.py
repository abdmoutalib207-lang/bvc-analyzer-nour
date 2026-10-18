"""Read-only inventory of remaining annual calculation gaps for every Nour issuer."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(report, facts):
    lines = ['# Couverture fondamentale des 80 titres', '',
        f"Date de calcul : {report['analysis_date']}. Inventaire des sorties du moteur, sans ajout de faits.", '',
        'BPA = bénéfice par action ; P/B = cours / valeur comptable. « Oui » signifie calcul disponible, '
        'pas comptes certifiés. Les BPA sur titres de clôture restent indicatifs. '
        'Un cours trop ancien peut suspendre P/B et PER sans supprimer les comptes annuels.', '',
        '| Titre | Annuel | BPA | P/B | ROE clôture | Revue primaire du lot | Travail restant / limite |',
        '|---|---|---|---|---|---|---|']
    for row in sorted(report['results'], key=lambda r:r['symbol']):
        symbol = row['symbol']; f = row['fundamental']; raw = facts.get(symbol) or {}; data = raw.get('faits') or {}
        review = raw.get('financial_review') or {}; tasks=[]
        if not f.get('document_url'):
            tasks.append('Rapport annuel récent à retrouver dans les sources autorisées')
        else:
            if not any(k in data for k in ('resultat_net_part_groupe','resultat_net_social')):
                tasks.append('Résultat attribuable/social manquant ; total non substitué')
            if not any(k in data for k in ('capitaux_propres_part_groupe','capitaux_propres_sociaux')):
                tasks.append('Fonds propres de même périmètre à relever')
            if f.get('eps_mad') is None and not any(k in data for k in ('nombre_actions','nombre_actions_au_rapport','nombre_actions_retenu_pour_le_bpa','nombre_actions_annuel_verifie')):
                tasks.append('Dénominateur annuel des actions à vérifier')
            if raw.get('capital_change_unresolved'):
                tasks.append('Capital modifié : rapprochement requis avant ratios au cours actuel')
            if raw.get('devise','MAD')!='MAD':tasks.append('Devise : pas de conversion MAD non documentée')
            if f.get('eps_mad') is not None and f.get('pe') is None and f['eps_mad']<=0:
                tasks.append('Perte/nul observé : PER positif non significatif')
            for item in raw.get('calculation_reservations') or []:
                if item.get('status')=='unresolved':tasks.append('BPA publié/dénominateur à rapprocher ; BPA et PER suspendus')
            if f.get('pb') is None and f.get('book_value_per_share_mad') is not None and not raw.get('capital_change_unresolved'):
                tasks.append('P/B non disponible : vérifier cours valide et fonds propres positifs')
            if f.get('debt_reconciliation',{}).get('status') in ('unresolved','cash_unresolved'):
                tasks.append('Dette/trésorerie non rapprochée ; restriction conservée')
            if not tasks:tasks.append('Poursuivre la revue des pièces, réserves, dividendes et KPI du métier')
        yes=lambda k:'Oui' if f.get(k) is not None else 'Indisponible'
        label=f"{symbol} · {row.get('name',symbol)}".replace('|','/')
        cols=[label,str(f.get('exercise') or 'Absent'),yes('eps_mad'),yes('pb'),yes('roe_pct'),str(review.get('reviewed_at') or 'Pas de revue annuelle dans ce champ'),'; '.join(dict.fromkeys(tasks))]
        lines.append('| '+' | '.join(x.replace('|','/') for x in cols)+' |')
    absent=sum(row['fundamental'].get('eps_mad') is None for row in report['results'])
    lines+=['',f"Les {len(report['results'])} titres sont inventoriés, y compris ceux sans publication récente. "
            f'Les {absent} BPA absents ne sont pas tous des oublis : dénominateurs, conflits internes, '
            'devises et opérations sur capital imposent des travaux différents. '
            'Ne pas déduire une absence de document de la seule indisponibilité d’un ratio.', '',
            'Reproduction : `python tools/inventory_fundamentals.py --output docs/fundamental-coverage-2026-10-18.md`.']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    report=json.loads((ROOT/'web/report.json').read_text());facts=json.loads((ROOT/'data/facts_reference.json').read_text())['records']
    text=inventory(report,facts)
    if a.output:a.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
