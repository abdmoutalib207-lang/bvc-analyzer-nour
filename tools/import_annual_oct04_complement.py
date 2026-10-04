"""Selected primary pages reviewed on 2026-10-04; no whole-report certification.

Replays only MGL/MRL/MDP/CASH annual facts and preserves semester inputs.
Original PDFs are recoverable through the URLs and SHA-256 below.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'MGL': ('Maghrebail_RFA_2025.pdf', 'b42dcbe782557763fa221dc7e0a1d8b27d89389694609a8d384e04bfb56f5d5b', 78),
    'MRL': ('MLE_RFA_2025.pdf', 'c2e2497885b96a859ccbcdd7a01dc61be13d0bf7017403f6ff79517dfad09aa5', 59),
    'MDP': ('Med_Paper_RFA_2025.pdf', '1c38089c7767c9d8d14d2f040bf10b7abd5ba07a97b431ff1e10c044e560e6b7', 84),
    'CASH': ('Cash_Plus_RFA_2025.pdf', 'e4a200dc1e2048a14280f411adeff0163090e697d7f743562e50a397ead4f090', 108),
}


def additions():
    records = {}

    def record(symbol, company, basis, warnings, rows, financial=False):
        filename, digest, pages = SOURCES[symbol]
        url = 'https://www.ammc.ma/sites/default/files/' + filename
        facts = {}
        for key, value, page, unit, note in rows:
            facts[key] = dict(valeur=value, page=page, unite=unit, devise='MAD',
                unite_au_rapport='actions' if unit == 'actions' else 'KMAD',
                url=url, base=basis, note=note, document_hash='sha256:' + digest,
                validation_status='pdf_page_visually_checked_2026-10-04')
        records[symbol] = dict(societe=company, exercice=2025, exercice_clos='2025-12-31',
            document='Rapport financier annuel 2025 : pages sélectionnées', url=url,
            pages_document=pages, devise='MAD', accounting_basis=basis, faits=facts,
            financial_business=financial, reservations=warnings,
            provenance=dict(source_type='regulator_pdf', source_url=url,
                document_hash='sha256:' + digest, reviewed_at='2026-10-04',
                validation_status='selected_pages_visually_checked_not_whole_report_certified'))

    record('MGL', 'Maghrebail', 'Social, plan comptable des établissements de crédit, 31/12/2025', [
        'Le graphique p.6 affiche 1 155 MMAD de fonds propres ; le bilan p.44 et le total du tableau p.57 concordent à 1 228,220 MMAD. Les tableaux détaillés sont retenus et cet écart reste signalé.',
        'BPA indicatif sur les 1 384 182 titres de clôture ; pas une moyenne pondérée auditée.',
        'Produit net financier distinct du CA. Le dividende distribué en 2025 concerne le résultat 2024 : il ne sert pas de dividende de l’exercice 2025.'
    ], [
        ('resultat_net_social', 148.199, 46, 'MMAD', '148 199 KMAD / 1 000 ; recoupé au bilan p.44.'),
        ('capitaux_propres_sociaux', 1228.220, 57, 'MMAD', 'Total 1 228 220 KMAD / 1 000 ; même somme au passif p.44 : 415 158 + 138 418 + 526 445 + 148 199. Hors provisions et dettes.'),
        ('nombre_actions_au_rapport', 1384182, 67, 'actions', 'Total capital publié, identique en 2024 et 2025 ; 138 418 200 MAD / nominal 100 MAD.'),
        ('produit_net_bancaire', 438.374, 46, 'MMAD', 'Ligne III « Produit net », 438 374 KMAD / 1 000 ; pas les produits d’exploitation 4 601 755 KMAD.'),
        ('produit_net_bancaire_2024', 377.618, 46, 'MMAD', '377 618 KMAD / 1 000 ; même tableau, même périmètre.'),
    ], financial=True)

    record('MRL', 'Maroc Leasing', 'Social, plan comptable des établissements de crédit, 31/12/2025', [
        'Fonds propres stricts 1 227,913 MMAD : hors dette subordonnée de 120,109 MMAD. Le total propres et assimilés ne sert pas de valeur comptable.',
        'PNB 2024 du CPC p.40 retenu à 379,187 MMAD ; le résumé p.14 indique 379,186 MMAD, écart de 1 KMAD conservé.',
        'Nombre de titres calculé à partir du capital exact p.4 et du nominal AMMC 100 MAD ; recoupé avec la fiche émetteur BVC 2025. BPA indicatif sur les titres de clôture.'
    ], [
        ('resultat_net_social', 107.295, 40, 'MMAD', '107 295 KMAD / 1 000 ; recoupé au passif p.38.'),
        ('capitaux_propres_sociaux', 1227.913, 55, 'MMAD', 'Total 1 227 913 KMAD / 1 000 ; somme des lignes 11, 12, 14, 16 du passif p.38. Dette subordonnée exclue.'),
        ('nombre_actions_au_rapport', 2776768, 4, 'actions', 'Calcul : capital exact 277 676 800 MAD / nominal 100 MAD (https://www.ammc.ma/fr/instruments-financiers/actions/action-maroc-leasing-sa), recoupé avec https://www.casablanca-bourse.com/en/live-market/emetteurs/MLE270297 ; pas une déduction à partir d’un capital arrondi au KMAD.'),
        ('produit_net_bancaire', 387.199, 40, 'MMAD', '387 199 KMAD / 1 000 ; PNB, pas produits d’exploitation bancaire.'),
        ('produit_net_bancaire_2024', 379.187, 40, 'MMAD', '379 187 KMAD / 1 000 ; colonne 2024 du CPC.'),
    ], financial=True)
    records['MRL']['semester_activity_label'] = 'PNB'

    record('MDP', 'Med Paper', 'Social, CGNC, 31/12/2025', [
        'Résultat net positif de 6,7131055 MMAD avec perte d’exploitation de 10,35552586 MMAD et résultat non courant positif de 22,12620377 MMAD ; le ROE ne mesure pas une rentabilité récurrente.',
        'Le tableau du capital p.80 totalise 4 714 199 titres, incompatible avec le capital 47 838 230 MAD au nominal 10 MAD. Le communiqué primaire T4 2025 confirme explicitement 4 783 823 actions : ce dénominateur recoupé est retenu.',
        'BPA indicatif sur les titres de clôture ; ni prévision 2026 ni colonnes « opérations propres à l’exercice » substituées aux totaux annuels.'
    ], [
        ('resultat_net_social', 6.71310550, 40, 'MMAD', 'Total exercice 6 713 105,50 MAD / 1 000 000 ; pas 9 666 867,24 avant imputation des opérations d’exercices précédents. Recoupé p.38.'),
        ('capitaux_propres_sociaux', 41.14596811, 38, 'MMAD', 'Total A 41 145 968,11 MAD / 1 000 000 ; pas le total du financement permanent.'),
        ('chiffre_affaires', 88.40888533, 39, 'MMAD', '88 408 885,33 MAD / 1 000 000 ; chiffre d’affaires, pas total produits d’exploitation.'),
        ('chiffre_affaires_2024', 105.56386554, 39, 'MMAD', '105 563 865,54 MAD / 1 000 000 ; même ligne, colonne précédent.'),
    ])
    for fact in records['MDP']['faits'].values():
        fact['unite_au_rapport'] = 'MAD'
    records['MDP']['faits']['nombre_actions_au_rapport'] = dict(valeur=4783823, page=1,
        unite='actions', unite_au_rapport='actions', devise='MAD', base=records['MDP']['accounting_basis'],
        url='https://www.ammc.ma/sites/default/files/CP_Med_Paper_T4_2025.pdf',
        document_hash='sha256:9df850466cc4cf09a561028309ddf3226c8eeb0b3beaa35f6a7ab043c0235f44',
        validation_status='pdf_page_visually_checked_2026-10-04',
        note='En-tête du communiqué T4 au 31/12/2025 : 4 783 823 actions au nominal de 10 MAD ; concorde avec capital exact 47 838 230 MAD du bilan annuel. Le total incomplet de l’ETIC p.80 n’est pas utilisé.')

    record('CASH', 'Cash Plus', 'Consolidé IFRS, part du groupe, 31/12/2025', [
        'Résultat net part du groupe 242,296 MMAD, distinct du total consolidé 241,283 MMAD (minoritaires négatifs).',
        'Fonds propres groupe à rapprocher : total publié p.68 de 790,351 MMAD contre somme des lignes part groupe du bilan p.65 de 790,776 MMAD (écart 0,425 MMAD). P/B et ROE restent indisponibles.',
        'La note 16 p.76 publie 24 553 090 actions de clôture et un passage du nominal de 100 à 10 MAD. Les lignes intermédiaires attribuent 22 297 781 actions à l’IPO de 20 000 KMAD et 1 712 809 actions à 171 281 KMAD : rapprochement des subdivisions/augmentations requis ; aucune moyenne pondérée n’est vérifiée.',
        'BPA/PER retenus indisponibles malgré le BPA publié 9,87 MAD p.78. Le nombre de clôture et le résultat sont conservés pour audit sans débloquer un ratio ambigu.',
        'PNB distinct du CA ; aucun ratio de dette industrielle. Semestre 2026 conservé sans annualisation.'
    ], [
        ('resultat_net_part_groupe', 242.296, 66, 'MMAD', '242 296 KMAD / 1 000 ; page imprimée 130, recoupé au bilan p.65 et note BPA p.78.'),
        ('produit_net_bancaire', 863.267, 66, 'MMAD', '863 267 KMAD / 1 000 ; pas marge sur commissions ni total commissions.'),
        ('produit_net_bancaire_2024', 759.840, 66, 'MMAD', '759 840 KMAD / 1 000 ; même ligne et périmètre.'),
        ('capitaux_propres_part_groupe_a_rapprocher', 790.351, 68, 'MMAD', '790 351 KMAD / 1 000 ; page imprimée 134-135. Valeur d’audit, non utilisée dans les ratios.'),
        ('nombre_actions_existant_a_rapprocher', 24553090, 76, 'actions', 'Nombre publié au 31/12/2025, nominal 10 MAD ; identique dans la note 25 p.78. Conservé sans calcul tant que les opérations de capital ne sont pas rapprochées.'),
    ], financial=True)
    records['CASH']['capital_change_unresolved'] = True
    records['CASH']['semester_activity_label'] = 'PNB'
    return records


def merge(data):
    result = copy.deepcopy(data)
    for symbol, annual in additions().items():
        previous = result['records'].get(symbol, {})
        if previous.get('latest_report'):
            annual['latest_report'] = copy.deepcopy(previous['latest_report'])
            annual['latest_report'].setdefault('provenance', copy.deepcopy(previous.get('provenance', {})))
        result['records'][symbol] = annual
    return result


def main():
    path = ROOT / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
