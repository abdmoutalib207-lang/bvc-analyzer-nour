"""Replay the selected ADI primary pages reviewed on 2026-10-11.

No network call, no overwrite of a newer exercise, no change to the S1 record.
PDF SHA256 and review scope are in docs/sector-quality-2026-10-11.md.
"""
from copy import deepcopy
import json
from pathlib import Path

URL = 'https://www.ammc.ma/sites/default/files/ADI_RFA_2025.pdf'
HASH = 'sha256:0d076ef448b6228ec8ff2ad60c2368044382d545ef84f51afb133636e4c538bc'
BASIS = 'consolidé (normes marocaines)'


def merge(document):
    out = deepcopy(document)
    r = out['records']['ADI']
    if r.get('exercice') != 2025:
        return out
    if r.get('url') != URL:
        raise ValueError('ADI: unexpected annual document; new review required')
    facts = r['faits']
    entries = {
        'resultat_net_part_groupe': (407.601, 22, 2025),
        'capitaux_propres_part_groupe': (3993.181, 21, 2025),
        'capitaux_propres_part_groupe_2024': (3668.286, 21, 2024),
        'capitaux_propres_consolides': (4084.918, 21, 2025),
        'chiffre_affaires': (2431.512, 22, 2025),
        'chiffre_affaires_2024': (2363.364, 22, 2024),
    }
    for key, (value, page, year) in entries.items():
        facts[key] = {**facts.get(key, {}), 'valeur': value, 'page': page,
            'unite': 'MMAD', 'unite_au_rapport': 'KMAD', 'valeur_au_rapport': value*1000,
            'url': URL, 'document_hash': HASH, 'base': BASIS,
            'period_end': f'{year}-12-31', 'printed_page': page,
            'validation_status': 'selected_pages_visually_checked',
            'note': 'Colonne annuelle contrôlée visuellement dans le tableau consolidé ; KMAD convertis en MMAD.'}
    facts['nombre_actions'] = {**facts['nombre_actions'], 'valeur': 22078588,
        'page': 50, 'printed_page': 50, 'unite': 'actions', 'url': URL,
        'document_hash': HASH, 'period_end': '2025-12-31',
        'validation_status': 'selected_pages_visually_checked',
        'note': 'Tableau de répartition du capital : 22 078 588 titres, total 2 207 858 800 MAD, nominal 100 MAD. Titres émis de clôture ; ne certifie ni une moyenne pondérée ni une absence d’actions propres.'}
    r['financial_review'] = {
        'reviewed_at': '2026-10-11', 'document_url': URL, 'document_hash': HASH,
        'pages': [21, 22, 50],
        'method': 'Lecture visuelle de pages PDF, contrôle des colonnes et conversion KMAD / MMAD. Le semestre et les autres postes importés ne sont pas recertifiés.',
        'conclusion': 'RNPG et fonds propres groupe confirmés. CA exact retenu au lieu du résumé arrondi. Fonds propres groupe 2024 ajoutés pour un ROE moyen séparé du score. Dette nette non rapprochée : multiple suspendu.'}
    r['external_references'] = [{
        'name': 'Simply Wall St · ADI',
        'url': 'https://simplywall.st/stocks/ma/real-estate-management-and-development/cbse-adi/alliances-developpement-immobilier-shares/information',
        'role': 'secondary_reference_only', 'reviewed_at': '2026-10-11',
        'note': 'Consultation complémentaire : dates et normalisations peuvent différer. Vérifier la période, le périmètre groupe/total et le nombre d’analystes. Aucun chiffre, objectif ou score externe ne remplace les comptes primaires Nour.'}]
    return out


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2)+'\n')
