"""Five annual primary reports, selected pages visually checked 2026-10-04."""
import json
from pathlib import Path

from tools.import_annual_oct04_complement import merge as merge_annual

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.ammc.ma/sites/default/files/'
SOURCES = {
    'ATW': ('AWB_RFA_2025.pdf', '766da5ac174bfd22e1a9aac59fd5465bb51b2249ed8143268afba5235f1e3afb', 156),
    'BCP': ('BCP_RFA_2025_compressed.pdf', 'f5cc9b4a00d4d3a2ab9022c98e31ea03898234f496acadffa5bdac75254cf34e', 144),
    'BMC': ('BMCI_RFA_2025_def.pdf', '03698726cef97d5dab8fbd13a9707cd3d1e5110f12a2ea11e3cf8f1415b924e6', 357),
    'BOA': ('BOA_RFA_2025_0.pdf', 'efa362d596424de1f676a12e047384de9a4ab4277bc030b21753d37c9326b347', 177),
    'SAF': ('Sanlam_RFA_2025.pdf', '77cd2b4d50e2094e4f9a7f55a4a383f48ec6d05b64583a9016855a39767fd327', 82),
}


def additions():
    records = {}
    for symbol, company, rows, warnings, blocked in [
        ('ATW', 'Attijariwafa bank', [
            ('resultat_net_part_groupe', 10644.852, 96, 'MMAD', 'RNPG 10 644 852 KMAD ; total avec minoritaires 12 368 271 exclu.'),
            ('capitaux_propres_part_groupe', 69431.269, 95, 'MMAD', 'Somme des lignes groupe : 14 655 001 + 43 422 960 + 708 456 + 10 644 852 = 69 431 269 KMAD. Total 80 490 370 hors minoritaires 11 059 101.'),
            ('produit_net_bancaire', 34921.384, 96, 'MMAD', 'PNB IFRS, distinct du CA et des produits bancaires bruts.'),
            ('produit_net_bancaire_2024', 34507.117, 96, 'MMAD', 'Comparatif du même CPC IFRS ; pas un résumé sur un autre référentiel.'),
            ('nombre_actions_au_rapport', 215140839, 110, 'actions', '215 140 839 actions ordinaires, nominal 10 MAD, capital exact 2 151 408 390 MAD.'),
        ], [
            'BPA indicatif sur les titres ordinaires de clôture ; une moyenne pondérée hors autocontrôle n’est pas identifiée. La note p.110 signale 13 602 015 actions détenues par le groupe, déduites des fonds propres pour 2 600 MMAD. Le quotient de clôture concorde avec le BPA publié 49,48 MAD, sans certifier sa méthode.',
            'PNB 2024 du CPC IFRS retenu à 34 507,117 MMAD ; les comparatifs d’autres résumés ne sont pas substitués à cette base.',
        ], False),
        ('BCP', 'Banque Centrale Populaire', [
            ('resultat_net_part_groupe', 4503.361, 31, 'MMAD', 'RNPG 4 503 361 KMAD ; total 5 621 085 exclu.'),
            ('capitaux_propres_part_groupe', 36974.989, 30, 'MMAD', '31 203 153 + 2 228 023 - 959 548 + 4 503 361 = 36 974 989 KMAD. Hors minoritaires 20 981 040 ; FSG 4 477 044 séparés au passif et non ajoutés.'),
            ('produit_net_bancaire', 26985.158, 31, 'MMAD', 'PNB IFRS du Groupe BCP ; pas le CA social de la seule BCP p.66.'),
            ('produit_net_bancaire_2024', 25601.207, 31, 'MMAD', 'Comparatif IFRS du même CPC.'),
            ('nombre_actions_au_rapport', 203312473, 66, 'actions', 'Total explicite de répartition du capital : 203 312 473, identique 2024/2025.'),
        ], [
            'ROE sur RNPG et fonds propres groupe de clôture IFRS hors fonds spéciaux de garantie ; ne représente pas le ROE de gestion sur fonds propres moyens ou intégrant ces fonds.',
            'BPA indicatif sur les titres de clôture ; quotient 22,15 MAD, cohérent avec le CPC, sans moyenne pondérée certifiée par Nour.',
        ], False),
        ('BMC', 'BMCI', [
            ('resultat_net_part_groupe', 434.829, 15, 'MMAD', 'RNPG 434 829 KMAD ; RN consolidé total 420 182, avec minoritaires négatifs, exclu.'),
            ('capitaux_propres_part_groupe', 7572.464, 15, 'MMAD', 'Ligne explicite Part du groupe 7 572 464 KMAD, recoupée au tableau p.16 ; total 7 583 624 exclu.'),
            ('produit_net_bancaire', 3943.792, 15, 'MMAD', 'PNB du CPC consolidé IFRS.'),
            ('produit_net_bancaire_2024', 3788.722, 15, 'MMAD', 'Comparatif du même CPC.'),
            ('nombre_actions_au_rapport', 13279286, 19, 'actions', 'Nombre explicite 13 279 286, identique 2024/2025, capital exact 1 327 928 600 MAD.'),
        ], [
            'BPA indicatif de clôture 32,74 MAD ; le rapport arrondit le résultat par action à 33 MAD. RNPG supérieur au total du fait des pertes minoritaires, sans substitution.',
            'Les tableaux consolidés sont accompagnés d’une attestation d’examen limité p.19 ; les pages sélectionnées ne valent pas certification du rapport par Nour.',
        ], False),
        ('BOA', 'Bank of Africa', [
            ('resultat_net_part_groupe', 3813.552, 120, 'MMAD', 'RNPG 3 813 552 KMAD, hors minoritaires.'),
            ('capitaux_propres_part_groupe', 31794.360, 121, 'MMAD', 'Colonne explicite groupe 31 794 360 KMAD ; somme du bilan p.120 concordante. Total 40 426 438 exclu.'),
            ('produit_net_bancaire', 20338.747, 120, 'MMAD', 'PNB consolidé IFRS.'),
            ('produit_net_bancaire_2024', 18716.574, 120, 'MMAD', 'Comparatif du même CPC.'),
            ('nombre_actions_existant_a_rapprocher', 220281881, 135, 'actions', 'Capital exact 2 202 818 810 MAD / 10 MAD ; 2024 : 215 786 333 titres. Clôture, sans moyenne pondérée validée.'),
        ], [
            'Capital modifié en 2025 : 215 786 333 à 220 281 881 titres. La note p.135 affiche un BPA 17,31 MAD sur le nombre publié mais ne fournit pas une moyenne pondérée explicitement réconciliée. Les opérations 2026 et les ajustements comparatifs restent à contrôler ; BPA/PER/P/B indisponibles.',
        ], True),
        ('SAF', 'Sanlam Maroc', [
            ('resultat_net_part_groupe', 676.523, 9, 'MMAD', 'RNPG consolidé IFRS 676 523 KMAD ; résultat social 451,62989795 MMAD distinct et non substitué.'),
            ('capitaux_propres_part_groupe', 6062.749, 9, 'MMAD', 'Groupe 6 062 749 KMAD, recoupé p.55 ; total 6 062 792 incluant 43 KMAD minoritaires exclu.'),
        ], [
            'ROE annuel historique sur le groupe Sanlam au 31/12/2025, avant fusion Allianz en 2026. Ne représente pas le groupe après fusion.',
            'Fusion et augmentation de capital 2026 : titres et périmètres entre périodes à rapprocher ; BPA/PER/P/B indisponibles. Aucun dividende ancien ramené à un nombre de titres nouveau.',
            'Produits des activités d’assurance IFRS 17 distincts des primes émises. Aucun PNB bancaire, CA générique ni ratio de dette industrielle dérivé de ces lignes.',
        ], True),
    ]:
        filename, digest, pages = SOURCES[symbol]
        url = BASE + filename
        basis = 'Consolidé IFRS, part du groupe, 31/12/2025'
        records[symbol] = dict(societe=company, exercice=2025, exercice_clos='2025-12-31',
            document='Rapport financier annuel 2025 : pages sélectionnées', url=url,
            pages_document=pages, devise='MAD', accounting_basis=basis,
            financial_business=True, capital_change_unresolved=blocked,
            semester_activity_label='PNB' if symbol != 'SAF' else 'Produits d’assurance IFRS 17',
            reservations=warnings, faits={key: dict(valeur=value, page=page, unite=unit,
                devise='MAD', unite_au_rapport='actions' if unit == 'actions' else 'KMAD',
                url=url, base=basis, note=note, document_hash='sha256:' + digest,
                validation_status='pdf_page_visually_checked_2026-10-04')
                for key, value, page, unit, note in rows},
            provenance=dict(source_type='regulator_pdf', source_url=url,
                document_hash='sha256:' + digest, reviewed_at='2026-10-04',
                validation_status='selected_pages_visually_checked_not_whole_report_certified'))
    records['SAF']['faits']['nombre_actions_post_fusion_2026_a_rapprocher'] = dict(
        valeur=5341874, page=1, unite='actions', unite_au_rapport='actions', devise='MAD',
        url=BASE + 'CP_Sanlam_Maroc_post_AGE_02_07_26.pdf',
        document_hash='sha256:43ae7b52a6a452a178ac7ca8ab7bf3ce510d9390ebdf593cf261046d51e77f34',
        validation_status='pdf_page_visually_checked_2026-10-04',
        base='Capital post fusion 2026, distinct du groupe annuel 2025',
        note='Capital 411 687 400 à 534 187 400 MAD / nominal 100 ; émission 1 225 000 titres. Admission annoncée 08/07/2026, effet comptable rétroactif 01/01/2026. Le nombre actuel ne divise pas le RN ou les fonds propres historiques sans rapprochement du nouveau périmètre.')
    return records


def merge(data):
    return merge_annual(data, additions())


if __name__ == '__main__':
    path = ROOT / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2) + '\n')
