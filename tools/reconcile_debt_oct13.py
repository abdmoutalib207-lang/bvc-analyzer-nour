"""Replay selected primary annual pages; preserve semesters and newer accounts."""
from copy import deepcopy
import json
from pathlib import Path

DOCUMENTS = {
    'ADI': ('ADI_RFA_2025.pdf', '0d076ef448b6228ec8ff2ad60c2368044382d545ef84f51afb133636e4c538bc'),
    'MNG': ('Managem_RFA_2025.pdf', 'c55a5149908f04488db23af43ff3e952dbeb72126a7ec00836f7b7452f648506'),
    'MUT': ('Mutandis_RFA_2025.pdf', '3bf8f03a9f054642164ac8c2b1eead5ef4729411b6e3fd89dfa2bc963e46f342'),
}


def merge(document):
    out = deepcopy(document)
    for symbol, (filename, digest) in DOCUMENTS.items():
        record = out['records'][symbol]
        if record.get('exercice') != 2025:
            continue
        url = 'https://www.ammc.ma/sites/default/files/' + filename
        if record.get('url') != url:
            raise ValueError(f'{symbol}: new primary document requires a new review')
        basis = 'consolidé (normes marocaines)' if symbol == 'ADI' else 'consolidé IFRS'

        def put(key, value, page, printed, year=2025, note=None):
            old = record['faits'].get(key, {})
            original_unit = 'MMAD' if symbol == 'MNG' or key == 'endettement_net' else 'KMAD'
            record['faits'][key] = {**old, 'valeur': value, 'unite': 'MMAD',
                'unite_au_rapport': original_unit, 'valeur_au_rapport': value if original_unit == 'MMAD' else value*1000,
                'page': page, 'printed_page': printed, 'period_end': f'{year}-12-31',
                'base': basis, 'url': url, 'document_hash': 'sha256:' + digest,
                'validation_status': 'selected_pages_visually_checked',
                'note': note if note is not None else old.get('note', '')}

        if symbol == 'ADI':
            for key, value, page in [('dettes_financieres', 2114.079, 21),
                    ('tresorerie_actif', 752.590, 21), ('endettement_net', 1303, 17)]:
                put(key, value, page, page)
            put('dettes_contrats_credit_bail', 60.916, 27, 27,
                note='Composante déjà incluse dans les dettes financières ; pas un ajustement de rapprochement vérifié.')
            record['faits']['dettes_financieres']['note'] = ('Dette de financement 1 980,718 + trésorerie-passif 133,361 MMAD. '
                'Écart de 58,489 MMAD avec la publication non expliqué. Retirer le crédit-bail ne constitue pas une définition documentée ; ratios suspendus.')
            conclusion = 'Écart ADI confirmé ; pas de définition publiée permettant un pont complet. Dette et multiple restent suspendus.'
            pages = [17, 21, 27]
        elif symbol == 'MNG':
            for key, value, page, printed in [('dettes_financieres',15323.5,86,171),
                    ('tresorerie_actif',4390.3,86,171), ('endettement_net',12674.4,68,135),
                    ('instruments_derives_couverture_passif',1707.9,86,171),
                    ('comptes_courants_associes_hors_perimetre_dette',33,68,134),
                    ('capitaux_propres_part_groupe',11478.3,86,171),
                    ('capitaux_propres_part_groupe_2024',10687.8,86,171),
                    ('resultat_net_part_groupe',3002.0,86,170),
                    ('excedent_brut_exploitation',5982,10,19)]:
                put(key,value,page,printed,year=2024 if key.endswith('_2024') else 2025)
            record['faits']['comptes_courants_associes_hors_perimetre_dette']['note'] = 'Montant arrondi lu sur le graphique CCA 2025 ; pas déduit comme solde de la différence.'
            record['faits']['comptes_courants_associes_hors_perimetre_dette']['label'] = 'Comptes courants d’associés hors périmètre'
            record['faits']['instruments_derives_couverture_passif']['label'] = 'Couvertures financières (MtM)'
            record['faits']['endettement_net']['valeur_au_rapport'] = 12674.4
            record['faits']['endettement_net']['unite_au_rapport'] = 'MMAD'
            record['faits']['endettement_net']['note'] = 'Indicateur élargi de la société : inclut MtM, locations et comptes courants hors intégration globale. Corps du commentaire : 12 674,4 MMAD ; graphique arrondi : 12 674.'
            record['faits']['dettes_financieres']['note'] = 'Emprunts et droits d’usage hors dérivés de couverture : 6 751,2 + 2 000 + 85,1 + 6 487,2 = 15 323,5 MMAD. Ne pas confondre avec la dette élargie de la société.'
            record['reservations'] = ['EBE annuel publié 5 982 MMAD (PDF p.10, imprimée p.19) : ce n’est pas un EBITDA IFRS recalculé. La dotation aux amortissements et provisions inclut des provisions.' if x.startswith('EBITDA = EBE') else x for x in record.get('reservations', [])]
            record['debt_scope_bridge'] = {
                'status': 'primary_components_checked', 'period_end': '2025-12-31',
                'component_keys': ['instruments_derives_couverture_passif', 'comptes_courants_associes_hors_perimetre_dette'],
                'definition': 'La dette financière nette calculée exclut les couvertures. Le chiffre société les inclut, ainsi que les comptes courants hors intégration globale. Le crédit-bail est déjà dans la dette calculée : ne pas le rajouter.',
            }
            conclusion = 'Pont contrôlé : 10 933,2 + 1 707,9 + 33 = 12 674,1 MMAD, face à 12 674,4 publiés. Résidu de 0,3 MMAD compatible avec les arrondis du graphique ; définitions distinctes conservées.'
            pages = [10, 68, 86]
        else:
            for key,value,page,printed in [('dettes_financieres',1248.950,54,106),
                    ('tresorerie_actif',259.728,54,106), ('endettement_net',828,40,79),
                    ('capitaux_propres_part_groupe',1551.387,54,106),
                    ('capitaux_propres_part_groupe_2024',1562.845,54,106),
                    ('resultat_net_part_groupe',126.161,54,107),
                    ('excedent_brut_exploitation',315.384,54,107)]:
                put(key,value,page,printed,year=2024 if key.endswith('_2024') else 2025)
            record['faits']['endettement_net']['note'] = 'Dette nette bancaire publiée, définition détaillée non trouvée. Ne pas assimiler à une dette financière nette globale ; aucun pont complet avec le bilan.'
            record['reservations'] = [x.replace('la valeur du bilan est publiée', 'les valeurs du bilan sont conservées pour contrôle, les ratios restent suspendus') for x in record.get('reservations', [])]
            conclusion = 'Bilan et annexe de dette recoupés (1 KMAD d’arrondi). Le pont vers la dette nette bancaire publiée reste absent ; dette et multiple suspendus.'
            pages = [40, 54, 62]
        record['debt_primary_review'] = {'reviewed_at':'2026-10-13', 'document_url':url,
            'document_hash':'sha256:'+digest, 'pages':pages, 'conclusion':conclusion,
            'method':'Pages PDF rendues et lues ; pages imprimées conservées séparément. Contrôle annuel uniquement, aucun remplacement du S1.'}
    return out


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2)+'\n')
