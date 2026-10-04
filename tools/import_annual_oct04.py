"""Reproducible, manually checked annual additions; originals stay outside git.

Inputs were visually checked in the AMMC PDFs on 2026-10-04. This imports
selected pages, not a certification of an entire report or a point-in-time base.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'AGM': ('Agma_RFA_2025.pdf', '7558ce34b46cbe9bf95d2c73a26cbe5cf2bd7aed678be5cde140ae65ac427f5c', 17),
    'SLM': ('Salafin_RFA_2025.pdf', '0f26aed96bc94fb23438c439b0de8a941cd61b6ee3ed0d7b4e5f7cb1cbb003cb', 106),
    'EQD': ('Eqdom_RFA_2025.pdf', 'a0b6f48f3391a3428f98a6b5ff21e924a692bdb838416d96594d1b677d7002d6', 74),
}


def additions():
    records = {}
    def record(ticker, company, basis, warnings, inputs, financial=False):
        filename, digest, pages = SOURCES[ticker]
        url = 'https://www.ammc.ma/sites/default/files/' + filename
        facts = {}
        for key, value, page, unit, note in inputs:
            facts[key] = dict(valeur=value, page=page, unite=unit, devise='MAD',
                url=url, base=basis, note=note, document_hash='sha256:' + digest,
                validation_status='pdf_page_visually_checked_2026-10-04')
        records[ticker] = dict(societe=company, exercice=2025, exercice_clos='2025-12-31',
            document='Rapport financier annuel 2025 : pages sélectionnées', url=url,
            pages_document=pages, devise='MAD', accounting_basis=basis, faits=facts,
            financial_business=financial, reservations=warnings,
            provenance=dict(source_type='regulator_pdf', source_url=url,
                document_hash='sha256:' + digest, reviewed_at='2026-10-04',
                validation_status='selected_pages_visually_checked_not_whole_report_certified'))
    record('AGM', 'AGMA', 'Social, CGNC, 31/12/2025', [
        'Le rapport annuel retenu présente les comptes sociaux ; le semestre disponible est consolidé IFRS. Ne pas les mélanger en TTM.',
        'Nombre d’actions non relevé dans ces pages : BPA, PER et P/B indisponibles ; aucune déduction à partir de la capitalisation.'
    ], [
        ('resultat_net_social', 71.02753751, 13, 'MMAD', '71 027 537,51 MAD / 1 000 000 ; CPC, colonne exercice 2025.'),
        ('capitaux_propres_sociaux', 153.61203091, 15, 'MMAD', '153 612 030,91 MAD / 1 000 000 ; total des capitaux propres A, hors assimilés et provisions.'),
        ('chiffre_affaires', 186.60788522, 13, 'MMAD', '186 607 885,22 MAD / 1 000 000 ; ventes de biens et services produits.'),
        ('chiffre_affaires_2024', 172.24939318, 13, 'MMAD', '172 249 393,18 MAD / 1 000 000 ; même tableau, exercice précédent.'),
    ])
    record('SLM', 'Salafin', 'Social, plan comptable des établissements de crédit, 31/12/2025', [
        'Capitaux propres calculés par addition des lignes du passif, hors 17,673 MMAD de provisions réglementées. Le total « propres et assimilés » ne sert pas au P/B.',
        'PNB distinct du chiffre d’affaires ; dette nette / EBE industriel non pertinent ici.',
        'Le dividende de 30 MAD figurant dans le projet d’affectation n’est pas traité comme approuvé.'
    ], [
        ('resultat_net_social', 96.117, 69, 'MMAD', '96 117 milliers de DH / 1 000 ; comptes sociaux.'),
        ('capitaux_propres_sociaux', 870.833, 68, 'MMAD', '(462 304 réserves et primes + 312 412 capital + 96 117 résultat) milliers de DH / 1 000 ; autres lignes de fonds propres nulles. Somme calculée, valeurs arrondies au KMAD.'),
        ('nombre_actions_au_rapport', 3124119, 57, 'actions', 'Nombre d’actions explicitement publié ; recoupé avec capital 312 411 900 MAD / nominal 100 MAD, page 89.'),
        ('produit_net_bancaire', 384.035, 69, 'MMAD', '384 035 milliers de DH / 1 000 ; PNB, pas CA.'),
        ('produit_net_bancaire_2024', 378.646, 69, 'MMAD', '378 646 milliers de DH / 1 000 ; PNB 2024, même tableau.'),
    ], financial=True)
    record('EQD', 'Eqdom', 'Consolidé, comptes des établissements de crédit, part du groupe, 31/12/2025', [
        'Capitaux propres groupe non utilisés : tableau de variation p.63 (1 485,722 MMAD) et somme des lignes du bilan p.58 (1 485,740 MMAD) diffèrent de 0,018 MMAD. Rapprochement requis ; P/B et ROE indisponibles.',
        'PNB distinct du chiffre d’affaires ; dette nette / EBE industriel non pertinent ici.',
        'BPA calculé sur les titres de clôture publiés, non sur une moyenne pondérée auditée.'
    ], [
        ('resultat_net_part_groupe', 98.561, 59, 'MMAD', '98 561 milliers de DH / 1 000, ligne 33 part du groupe, page imprimée 117 ; pas résultat total 99 261.'),
        ('nombre_actions_au_rapport', 1670250, 55, 'actions', 'Total publié de la répartition du capital ; capital 167 025 000 MAD / nominal 100 MAD ; page imprimée 108.'),
        ('produit_net_bancaire', 601.924, 59, 'MMAD', '601 924 milliers de DH / 1 000, consolidé, page imprimée 117.'),
        ('produit_net_bancaire_2024', 550.137, 59, 'MMAD', '550 137 milliers de DH / 1 000 ; même tableau, 2024.'),
        ('capitaux_propres_part_groupe_a_rapprocher', 1485.722, 63, 'MMAD', 'Valeur publiée dans le tableau de variation p. imprimée 124-125 ; conservée pour audit seulement, non utilisée dans les ratios.'),
    ], financial=True)
    return records


def main():
    path = ROOT / 'data/facts_reference.json'
    data = json.loads(path.read_text())
    for ticker, annual in additions().items():
        previous = data['records'].get(ticker, {})
        # Preserve semester evidence and its independent source provenance.
        if previous.get('latest_report'):
            annual['latest_report'] = previous['latest_report']
            annual['latest_report']['provenance'] = previous.get('provenance', {})
        data['records'][ticker] = annual
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
