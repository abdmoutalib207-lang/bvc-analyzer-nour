"""CIH/CDM selected AMMC pages visually reviewed on 2026-10-04.

Replays annual inputs and adds CIH S1 without overwriting existing semesters.
Per-share ratios remain blocked pending reconciliation of capital operations.
"""
import json
from pathlib import Path

from tools.import_annual_oct04_complement import merge as merge_annual

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.ammc.ma/sites/default/files/'
SOURCES = {
    'CIH': ('CIH_Bank_RFA_2025.pdf', 'fe67f5488c79c339dc40a61d4cba8b54f675849a6dc6a80db146ec9ef27fac96', 182),
    'CDM': ('CDM_RFA_2025.pdf', '11af272b57e92d54cc077b1d943ecff26c24c61972ca2a0c0464ab3c8796f692', 225),
}


def additions():
    records = {}
    for symbol, company, rows, warnings in [
        ('CIH', 'CIH Bank', [
            ('resultat_net_part_groupe', 1089.362, 25, 'MMAD', '1 089 362 KMAD / 1 000 ; hors minoritaires, résultat total 1 220 478 KMAD.'),
            ('capitaux_propres_part_groupe', 9768.468, 26, 'MMAD', 'Part groupe corrigée : 9 817 628 - 49 160 = 9 768 468 KMAD ; recoupée avec les lignes groupe du bilan p.24. Hors total consolidé 10 731 487 KMAD.'),
            ('produit_net_bancaire', 5422.526, 25, 'MMAD', '5 422 526 KMAD / 1 000 ; PNB consolidé IFRS.'),
            ('produit_net_bancaire_2024', 4739.507, 25, 'MMAD', '4 739 507 KMAD / 1 000 ; même tableau et périmètre.'),
            ('nombre_actions_existant_a_rapprocher', 35605624, 52, 'actions', 'Nombre à la clôture 2025, capital exact 3 560 562 400 MAD / nominal 100 MAD. Conservé pour audit, sans dénominateur pondéré vérifié.'),
        ], [
            'Les fonds propres part groupe corrigés p.26 sont retenus ; ni le total avec minoritaires ni la ligne avant correction.',
            'Le nombre de titres passe de 31 497 283 à 35 605 624 en 2025 (tableau BPA p.36). Une moyenne pondérée n’est pas vérifiée. Le BPA publié 30,6 et le BPA dilué 3,7 p.25 ne débloquent aucun ratio.',
            'Les deux communiqués AMMC du 04/08/2026 confirment 38 641 338 titres après émission de 2 142 857 et 892 857 actions. Le capital actuel est recoupé, mais la moyenne pondérée 2025 et les ajustements par action entre périodes ne sont pas validés. BPA/PER/P/B bloqués ; ROE annuel historique conservé.',
        ]),
        ('CDM', 'Crédit du Maroc', [
            ('resultat_net_part_groupe', 863.551, 13, 'MMAD', '863 551 KMAD / 1 000 ; résultat net part groupe du CPC, page imprimée 14.'),
            ('capitaux_propres_part_groupe', 8203.010, 14, 'MMAD', 'Colonne explicite part Groupe : 8 203 010 KMAD / 1 000 ; intérêts minoritaires nuls, page imprimée 15.'),
            ('produit_net_bancaire', 3568.401, 13, 'MMAD', '3 568 401 KMAD / 1 000 ; PNB distinct du CA.'),
            ('produit_net_bancaire_2024', 3303.182, 13, 'MMAD', '3 303 182 KMAD / 1 000 ; même ligne et périmètre.'),
            ('nombre_actions_existant_a_rapprocher', 10881214, 24, 'actions', 'Total du capital 2025 : 5 941 968 + 1 201 744 + 1 168 523 + 2 568 979 = 10 881 214 ; nominal 100 MAD, page imprimée 25. Ne représente pas les actions après augmentation 2026.'),
        ], [
            'Le résumé affiche un RNPG par action de 79,44 DH, contre 79,36 au CPC. Le quotient des entrées annuelles exactes donne 79,36 ; ce rapprochement historique ne valide pas le nombre actuel de titres.',
            'Le communiqué du 28/07/2026 confirme l’émission de 745 285 actions : 10 881 214 + 745 285 = 11 626 499 titres, cohérents avec le nouveau capital 1 162 649 900 MAD / nominal 100 MAD. Le nombre actuel est recoupé ; les ajustements comparatifs par action et la comparabilité au cours actuel restent à valider. BPA/PER/P/B indisponibles.',
            'Le semestre 2026 importé reste conservé avec sa provenance et son statut de référence non auditée indépendamment. PNB distinct du CA ; aucune annualisation du semestre.',
        ]),
    ]:
        filename, digest, pages = SOURCES[symbol]
        url = BASE + filename
        basis = 'Consolidé IFRS, part du groupe, 31/12/2025'
        facts = {key: dict(valeur=value, page=page, unite=unit, devise='MAD',
            unite_au_rapport='actions' if unit == 'actions' else 'KMAD',
            url=url, base=basis, note=note, document_hash='sha256:' + digest,
            validation_status='pdf_page_visually_checked_2026-10-04')
            for key, value, page, unit, note in rows}
        records[symbol] = dict(societe=company, exercice=2025, exercice_clos='2025-12-31',
            document='Rapport financier annuel 2025 : pages sélectionnées', url=url,
            pages_document=pages, devise='MAD', accounting_basis=basis, faits=facts,
            financial_business=True, capital_change_unresolved=True,
            semester_activity_label='PNB', reservations=warnings,
            provenance=dict(source_type='regulator_pdf', source_url=url,
                document_hash='sha256:' + digest, reviewed_at='2026-10-04',
                validation_status='selected_pages_visually_checked_not_whole_report_certified'))
    for symbol, count, filename, digest, note in [
        ('CIH', 38641338, 'CP_CIH_Bank_resultats_augmentation_capital_numeraire.pdf',
         '47a9dce09225426479bb48ae2e5a335ce015fd52ee222418f6adb4aa0ceb7bce',
         'Capital après les deux opérations constatées le 28/07/2026 : 35 605 624 + 2 142 857 + 892 857 = 38 641 338. Recoupé avec le communiqué personnel ; ce nombre actuel ne sert pas de moyenne pondérée 2025 ni de dénominateur sur les anciens fonds propres.'),
        ('CDM', 11626499, 'CP_CDM_cloture_augmentation_capital.pdf',
         '347e452f5d148ced071a0941f720e8d68c01d549b4bff0df81cb45c43c57bd5f',
         'Capital après opération constatée le 23/07/2026 : 10 881 214 + 745 285 = 11 626 499 ; capital publié 1 162 649 900 MAD / nominal 100 MAD. Ne remplace pas les titres 2025 sans ajustement comparatif explicite.'),
    ]:
        records[symbol]['faits']['nombre_actions_post_augmentation_2026_a_rapprocher'] = dict(
            valeur=count, page=1, unite='actions', unite_au_rapport='actions', devise='MAD',
            url=BASE + filename, base='Capital après augmentation juillet 2026, distinct du périmètre annuel 2025',
            note=note, document_hash='sha256:' + digest, validation_status='pdf_page_visually_checked_2026-10-04')
    url = BASE + 'CIH_Bank_S1_26.pdf'
    records['CIH']['latest_report'] = dict(period_end='2026-06-30', document_url=url,
        accounting_basis='Résultat net part du groupe, consolidé IFRS', pages='PDF p.10, tableaux IFRS, milliers MAD',
        reported_net_millions=616.987, reported_net_previous_millions=615.437,
        revenue_millions=2825.752, revenue_previous_millions=2748.136, currency='MAD',
        note='PNB, pas CA. RNPG distinct du total 695,404 MMAD. Colonne juin 2025 comparable ; semestre non annualisé.',
        validation_status='pdf_page_visually_checked_2026-10-04',
        provenance=dict(source_type='regulator_pdf', source_url=url,
            document_hash='sha256:4938f7b50e5bd89a851aee1120a4aa8a7ba27df6090e7f355e52ca99e531ccc5',
            reviewed_at='2026-10-04', validation_status='selected_page_visually_checked_not_whole_report_certified'))
    return records


def merge(data):
    return merge_annual(data, additions())


def main():
    path = ROOT / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
