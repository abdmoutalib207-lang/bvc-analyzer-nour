"""Replay TMA primary pages visually checked on 2026-10-16, without networking.

The AMMC eight-page AGO communication contains 2025 IFRS accounts; it is not
labelled a full RFA. Preserve the existing S1 reference byte-for-byte as data.
Debt arithmetic is visible, but no industrial debt ratio without lease scope.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

URL = 'https://www.ammc.ma/sites/default/files/Total_2025_avis_AGO_03_06_26_0.pdf'
HASH = 'sha256:c199525c357c4e84a51221866305a50586e866310c1a627ef450bed6df0fb2f3'
S1_URL = 'https://www.ammc.ma/sites/default/files/Total_Maroc_S1_26.pdf'
S1_HASH = 'sha256:da3d59b5038415464640b87cc3c0a2f71c3ee3c67ffa689cab1496c428a0db96'
OLD_URL = 'https://www.ammc.ma/sites/default/files/Total_RFA_2024.pdf'
BASIS = 'consolidé IFRS'
STATUS = 'selected_pages_visually_checked'


def _fact(original, page=6, year=2025, unit='KMAD', url=URL, digest=HASH, note=''):
    return {'valeur': original / 1000 if unit == 'KMAD' else original,
            'valeur_au_rapport': original, 'unite': 'MMAD' if unit == 'KMAD' else unit,
            'unite_au_rapport': unit, 'devise': 'MAD', 'page': page,
            'period_end': f'{year}-12-31', 'base': BASIS, 'url': url,
            'document_hash': digest, 'validation_status': STATUS, 'note': note}


def merge(document):
    out = deepcopy(document)
    record = out['records']['TMA']
    if record.get('exercice') not in (2024, 2025):
        return out
    expected_url = OLD_URL if record['exercice'] == 2024 else URL
    if record.get('url') != expected_url:
        raise ValueError('TMA: unexpected annual source; new primary review required')
    complementary = record.get('complementary_reference_verified') or {}
    if complementary.get('document_hash') and complementary['document_hash'] != S1_HASH:
        raise ValueError('TMA: changed reviewed complementary source')
    if record.get('exercice') == 2025:
        digest = (record.get('financial_review') or {}).get('document_hash')
        if digest and digest != HASH:
            raise ValueError('TMA: changed reviewed annual source')
        for fact in record.get('faits', {}).values():
            if fact.get('document_hash') and fact['document_hash'] != HASH:
                raise ValueError('TMA: conflicting primary annual proof')
    else:
        record.setdefault('annual_reference_prior_oct16', {
            key: deepcopy(record.get(key)) for key in
            ('exercice', 'document', 'url', 'pages_document', 'faits', 'provenance', 'accounting_basis')})
    record.update(exercice=2025, exercice_clos='2025-12-31', url=URL,
                  document='Communication financière 2025 et avis AGO du 3 juin 2026 (comptes consolidés IFRS)',
                  pages_document=8, releve_le='2026-10-16', accounting_basis=BASIS, devise='MAD')
    entries = {
        'chiffre_affaires': (15126704, 2025),
        'chiffre_affaires_2024': (16751842, 2024),
        'resultat_net_part_groupe': (851083, 2025),
        'resultat_net_part_groupe_2024': (934195, 2024),
        'resultat_net_consolide': (851083, 2025),
        'capitaux_propres_part_groupe': (1984665, 2025),
        'capitaux_propres_part_groupe_2024': (2745769, 2024),
        'capitaux_propres_consolides': (1984665, 2025),
        'total_actif': (8258143, 2025),
        'total_passif': (8258143, 2025),
        'dettes_financieres_non_courantes_a_rapprocher': (514346, 2025),
        'dettes_financieres_courantes_a_rapprocher': (373609, 2025),
        'tresorerie_a_rapprocher': (1176535, 2025),
    }
    record['faits'] = {key: _fact(value, year=year) for key, (value, year) in entries.items()}
    record['faits']['nombre_actions'] = _fact(8960000, page=3, unit='actions',
        note='Nombre d’actions composant explicitement le capital au 31 décembre 2025, '
             'dans le projet de résolution. Pas une moyenne pondérée IAS 33 ; BPA calculé indicatif. '
             'Ni division du capital arrondi, ni inversion du BPA arrondi à 95 MAD.')
    record['faits']['nombre_actions_au_rapport'] = deepcopy(record['faits']['nombre_actions'])
    for key in entries:
        if key.endswith('_a_rapprocher'):
            record['faits'][key]['note'] = ('Poste du bilan publié ; périmètre des dettes de location non rapproché. '
                'Conservé pour contrôle, exclu du calcul de dette nette industrielle et du multiple.')
    record['provenance'] = {'source_type': 'regulator_pdf', 'source_url': URL,
        'document_hash': HASH, 'reviewed_at': '2026-10-16',
        'validation_status': 'selected_pages_visually_checked_not_whole_report_certified'}
    reservations = record.setdefault('reservations', [])
    for note in (
        'TMA : comptes IFRS annuels 2025 dans la communication AGO AMMC (8 pages), '
        'pas le RFA intégral. Actions de clôture publiées : BPA indicatif ; dividende proposé non retenu sans décision AGO.',
        'TMA : au S1 2026, postes de dette moins trésorerie = 326,343 MMAD, contre −288,580 MMAD fin 2025 '
        '(AMMC S1 p.4, mêmes postes). Périmètre des locations non rapproché : dette nette industrielle et multiple '
        'indisponibles ; le S1 reste distinct et non annualisé.',
    ):
        if note not in reservations:
            reservations.append(note)
    record['financial_review'] = {'reviewed_at': '2026-10-16', 'document_url': URL,
        'document_hash': HASH, 'pages': [3, 6, 7],
        'method': 'Pages PDF rendues et lues : actions de clôture p.3 ; comptes consolidés IFRS '
                  '2025/2024 et unités KMAD p.6 ; opinion des commissaires aux comptes p.7. '
                  'Contrôle de pages sélectionnées, sans certification du rapport entier.',
        'conclusion': 'RNPG 851,083 MMAD, fonds propres groupe 1 984,665 MMAD et 8 960 000 actions publiées. '
                      'Le résultat social de 802,568 MMAD n’est pas substitué au RNPG. '
                      'Ratios annuels fondés sur 2025 ; référence S1 préexistante préservée.'}
    s1_facts = {}
    for key, original in [('dettes_financieres_non_courantes', 473879),
                          ('dettes_financieres_courantes', 841200), ('tresorerie', 988736)]:
        fact = _fact(original, page=4, year=2026, url=S1_URL, digest=S1_HASH)
        fact['period_end'] = '2026-06-30'
        s1_facts[key] = fact
    record['complementary_reference_verified'] = {
        'period_end': '2026-06-30', 'document_url': S1_URL, 'document_hash': S1_HASH,
        'pages': [4], 'accounting_basis': BASIS, 'reviewed_at': '2026-10-16',
        'validation_status': STATUS, 'faits': s1_facts,
        'debt_components_mmad': {'noncurrent': 473.879, 'current': 841.200, 'cash': 988.736},
        'arithmetic_net_debt_mmad': 326.343, 'annual_comparative_net_debt_mmad': -288.580,
        'method': 'Dettes financières non courantes + courantes − trésorerie et équivalents ; '
                  'calcul arithmétique de postes, pas une définition de dette nette industrielle validée. '
                  'La colonne décembre 2025 p.4 confirme 514,346 + 373,609 − 1 176,535 = −288,580 MMAD.',
        'lease_debt_scope': 'unresolved', 'semester_annualized': False,
    }
    return out


def verify_pdf(path, semester=False):
    actual = 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != (S1_HASH if semester else HASH):
        raise ValueError('TMA: document hash changed; new primary review required')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pdf', type=Path, help='Official annual AGO PDF to hash-check')
    parser.add_argument('--semester-pdf', type=Path, help='Official S1 PDF to hash-check')
    args = parser.parse_args()
    if args.pdf:
        verify_pdf(args.pdf)
    if args.semester_pdf:
        verify_pdf(args.semester_pdf, semester=True)
    path = Path(__file__).resolve().parents[1] / 'data/facts_reference.json'
    before = json.loads(path.read_text())
    after = merge(before)
    if args.check:
        if after != before:
            raise SystemExit('TMA primary import not applied')
        print('TMA primary import: up to date')
        return
    path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
