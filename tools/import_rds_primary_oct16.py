"""Replay selected RDS annual primary pages visually reviewed on 2026-10-16.

No network, semester change or claim to certify the complete annual report.
The exact share count is published on p.23, never inferred from rounded capital.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

URL = 'https://www.ammc.ma/sites/default/files/RDS_RFA_2025.pdf'
HASH = 'sha256:af0e17be057fcc51f43834745462b8ca07dc9c9de506cf3340ca0330ca8576fd'
BASIS = 'consolidé IFRS'


def merge(document):
    out = deepcopy(document)
    r = out['records']['RDS']
    if r.get('exercice') != 2025:
        return out
    if r.get('url') != URL:
        raise ValueError('RDS: unexpected annual source; new primary review required')
    reviewed_hash = (r.get('financial_review') or {}).get('document_hash')
    if reviewed_hash and reviewed_hash != HASH:
        raise ValueError('RDS: reviewed document changed; new primary review required')
    r['exercice_clos'] = '2025-12-31'
    f = r['faits']
    r.setdefault('reconciliation_prior_oct16', deepcopy(f))
    entries = {
        'chiffre_affaires': (468513, 22, 2025),
        'chiffre_affaires_2024': (233682, 22, 2024),
        'resultat_net_part_groupe': (4494, 22, 2025),
        'resultat_net_part_groupe_2024': (-79675, 22, 2024),
        'resultat_net_consolide': (4491, 22, 2025),
        'capitaux_propres_part_groupe': (3739480, 26, 2025),
        'capitaux_propres_part_groupe_2024': (3735121, 26, 2024),
        'capitaux_propres_consolides': (3739578, 26, 2025),
        'total_actif': (7970234, 24, 2025),
        'total_passif': (7970234, 26, 2025),
        'dettes_financieres': (2116222, 26, 2025),
        'tresorerie_actif': (249215, 24, 2025),
    }
    for key, (original, page, year) in entries.items():
        known_hash = (f.get(key) or {}).get('document_hash')
        if known_hash and known_hash != HASH:
            raise ValueError(f'RDS: conflicting primary proof for {key}')
        f[key] = {**f.get(key, {}), 'valeur': original / 1000,
            'valeur_au_rapport': original, 'unite': 'MMAD', 'unite_au_rapport': 'KMAD',
            'page': page, 'printed_page': page, 'url': URL, 'document_hash': HASH,
            'base': BASIS, 'period_end': f'{year}-12-31',
            'validation_status': 'selected_pages_visually_checked'}
    for key in ('nombre_actions', 'nombre_actions_au_rapport'):
        f[key] = {'valeur': 26208850, 'valeur_au_rapport': 26208850,
            'unite': 'actions', 'unite_au_rapport': 'actions',
            'page': 23, 'printed_page': 23, 'url': URL, 'document_hash': HASH,
            'base': BASIS, 'period_end': '2025-12-31',
            'validation_status': 'selected_pages_visually_checked',
            'note': 'Nombre explicitement publié dans les tableaux BPA et dividendes. '
                    'L’en-tête KMAD concerne les montants, pas les 26 208 850 actions. '
                    'Ne pas déduire 26 208 860 actions du capital arrondi du bilan. '
                    'La table ne suffit pas à certifier séparément une moyenne pondérée IAS 33.'}
    f['capitaux_propres_part_groupe']['note'] = ('Fonds propres groupe 3 739 480 KMAD ; minoritaires 98 KMAD distincts. '
        'Le capital du bilan est arrondi : ne pas en déduire le nombre d’actions ; p.23 publie 26 208 850 titres.')
    reservations = r.setdefault('reservations', [])
    for note in (
        'RDS : changement de reconnaissance du CA à la signature de l’acte notarié '
        'en 2025 (RFA p.6). La croissance annuelle calculée n’est pas à méthode constante.',
        'RDS : le RFA p.83 renvoie au rapport d’audit consolidé sur le site émetteur ; '
        'ce rapport externe n’est pas relu par le présent contrôle de pages sélectionnées.',
    ):
        if note not in reservations:
            reservations.append(note)
    r['financial_review'] = {
        'reviewed_at': '2026-10-16', 'document_url': URL, 'document_hash': HASH,
        'pages': [9, 21, 22, 23, 24, 26],
        'method': 'Lecture visuelle de pages PDF, périodes 2025/2024, périmètre IFRS '
                  'consolidé et unités KMAD contrôlés. Le semestre reste inchangé et non recertifié.',
        'conclusion': 'RNPG 4,494 MMAD distinct du résultat total 4,491 ; fonds propres groupe '
                      '3 739,480 distincts du total 3 739,578. Nombre publié 26 208 850 actions, '
                      'corrigé au lieu de la division du capital arrondi. CA annuel 468,513 MMAD. '
                      'Dette nette calculée 1 867,007 MMAD, sans rapprochement à une définition '
                      'nette publiée ; pas de certification de tous les comptes.'}
    return out


def verify_pdf(path):
    actual = 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != HASH:
        raise ValueError('RDS: document hash changed; new primary review required')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check replay is up to date without modifying data')
    parser.add_argument('--pdf', type=Path, help='Independently downloaded official PDF to hash-check')
    args = parser.parse_args()
    if args.pdf:
        verify_pdf(args.pdf)
    path = Path(__file__).resolve().parents[1] / 'data/facts_reference.json'
    before = json.loads(path.read_text())
    after = merge(before)
    if args.check:
        if after != before:
            raise SystemExit('RDS primary import not applied')
        print('RDS primary import: up to date')
        return
    path.write_text(json.dumps(after, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
