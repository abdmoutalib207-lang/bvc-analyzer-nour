"""Targeted, replayable primary-source reconciliation; never changes the main engine."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = ('HAL', 'CASH', 'EQD', 'MGL', 'CDM', 'M2M')
HAL_CONSO = 'https://www.autohall.ma/uploads/investisseurs/fichiers/cd0440678fe9a6903ad441fcb850bd2e962ad130.pdf'
HAL_DR = 'https://www.autohall.ma/uploads/investisseurs/fichiers/d3b0c03d293c6f9e64acc788a5343f55d799a9a1.pdf'
HAL_CAP = 'https://www.autohall.ma/uploads/investisseurs/fichiers/89f147c64fb3e8e4739930c633beb6d69167dfe2.pdf'
HASH_CONSO = 'sha256:8eb890bbc68015f0629b94c6bf23bbee95e308b7dd2916dbdd6ec2e4bb1dc1ca'
HASH_DR = 'sha256:4857168c7bda54d12ed8eeffeeda0fa62e7bbfd191cbc6e29db4783eac0655a2'
HASH_CAP = 'sha256:975b364d767856bce72467d91351178d812e739287e3e286828b5bde76acc62a'
IPO = 'https://www.ammc.ma/sites/default/files/NO_CASHPLUS_036_2025.pdf'
HASH_IPO = 'sha256:0f85a59b615b94b857d155145a24901f51f35e9befa525c9737983695aa36103'
SOURCES = {
    'CASH': 'https://www.ammc.ma/sites/default/files/Cash_Plus_RFA_2025.pdf',
    'EQD': 'https://www.ammc.ma/sites/default/files/Eqdom_RFA_2025.pdf',
    'MGL': 'https://www.ammc.ma/sites/default/files/Maghrebail_RFA_2025.pdf',
    'CDM': 'https://www.ammc.ma/sites/default/files/CDM_RFA_2025.pdf',
    'M2M': 'https://www.ammc.ma/sites/default/files/M2M_Group_2025.pdf',
}
HASHES = {
    'CASH': 'sha256:e4a200dc1e2048a14280f411adeff0163090e697d7f743562e50a397ead4f090',
    'EQD': 'sha256:a0b6f48f3391a3428f98a6b5ff21e924a692bdb838416d96594d1b677d7002d6',
    'MGL': 'sha256:b42dcbe782557763fa221dc7e0a1d8b27d89389694609a8d384e04bfb56f5d5b',
    'CDM': 'sha256:11af272b57e92d54cc077b1d943ecff26c24c61972ca2a0c0464ab3c8796f692',
}


def fact(r, value, page, note, unit='MMAD', url=None, digest=None):
    return dict(valeur=value, page=page, unite=unit, devise='MAD',
                url=url or r['url'], document_hash=digest or r['provenance'].get('document_hash'),
                base=r['accounting_basis'], note=note,
                validation_status='selected_pages_reconciled_with_reservations_2026-10-05')


def review(r, conclusion, method):
    r['financial_review'] = dict(reviewed_at='2026-10-05', conclusion=conclusion, method=method)


def historical(r, count, page, note, url=None, digest=None):
    f = fact(r, count, page, note, 'actions', url, digest)
    f.update(period_end='2025-12-31', validation_status='historical_closing_shares_visually_checked')
    r['faits']['nombre_actions_annuel_verifie'] = f
    r['capital_change_unresolved'] = True


def merge(data):
    out = copy.deepcopy(data)
    for symbol in SYMBOLS:
        r = out['records'][symbol]
        if r.get('exercice', 0) > 2025:
            continue
        if r.get('exercice') != 2025:
            raise ValueError(f'{symbol}: exercice inattendu, vérification requise')
        if symbol != 'HAL' and r['url'] != SOURCES[symbol]:
            raise ValueError(f'{symbol}: source inattendue, vérification requise')
        if symbol in HASHES and r['provenance'].get('document_hash') != HASHES[symbol]:
            raise ValueError(f'{symbol}: empreinte modifiée, vérification requise')
        if symbol == 'HAL' and r['url'] not in (HAL_CONSO, 'https://www.ammc.ma/sites/default/files/Auto_Hall_RFA_2025_0.pdf'):
            raise ValueError('HAL: source inattendue')
        f = r['faits']
        if symbol == 'CASH':
            f['capitaux_propres_part_groupe'] = fact(r, 790.776, 65,
                'KMAD : 245531 + 385425 - 82476 + 242296 = 790776 ; recoupé p.68 : 781393 - (-8370 - 1013) = 790776. Sous-total groupe 790351 p.68 non utilisé.')
            for key in ('nombre_actions_au_rapport', 'nombre_actions_existant'):
                f[key] = fact(r, 24553090, 76,
                    'Clôture 2025 : capital 245530900 MAD / nominal 10 MAD ; recoupé note BPA p.78 et prospectus IPO p.39 après subdivision.', 'actions')
            r['capital_change_unresolved'] = False
            r['provenance']['corroborating_documents'] = [dict(source_url=IPO, document_hash=HASH_IPO, pages='PDF p.39')]
            r['reservations'] = [
                'RNPG 242,296 MMAD, distinct du total 241,283 MMAD. Fonds propres groupe retenus 790,776 MMAD, rapprochés bilan et total moins minoritaires ; sous-total p.68 de 790,351 conservé pour audit, non utilisé.',
                '24 553 090 titres de clôture recoupés au capital, à la note BPA et au prospectus IPO p.39. Les lignes intermédiaires de la note 16 ne sont pas utilisées ; aucune moyenne pondérée auditée n’est déduite.',
                'BPA/PER indicatifs sur les titres de clôture, pas BPA pondéré IAS 33. Comparatif 2024 non ajusté à la subdivision : aucune croissance de BPA calculée.',
                'PNB distinct du CA ; aucun ratio de dette industrielle. Semestre conservé sans annualisation.']
            review(r, 'Fonds propres groupe rapprochés : 790,776 MMAD ; capital de clôture recoupé : 24 553 090 actions.',
                'Bilan p.65 et total consolidé moins minoritaires p.68 donnent la même valeur. Note 16 p.76, note 25 p.78 et prospectus IPO p.39 recoupent les titres de clôture. BPA indicatif uniquement.')
        elif symbol == 'EQD':
            f['capitaux_propres_part_groupe'] = fact(r, 1485.722, 63,
                'Tableau de variation : groupe 1485722 + minoritaires 717 = total 1486439 KMAD. Bilan : total des composantes 1486440, moins minoritaires 18+699 = 1485723, écart résiduel 1 KMAD compatible avec les arrondis. La ligne réserves groupe du bilan répète le total 1136829 malgré minoritaires 18 ; ne pas additionner comme groupe.')
            r['reservations'] = [
                'Fonds propres groupe retenus 1 485,722 MMAD, tableau de variation p.63. Le bilan p.58 répète le total des réserves en part groupe malgré 18 KMAD minoritaires ; total moins minoritaires recoupe à 1 KMAD près. Réserve d’arrondi conservée, pas rectification du PDF par Nour.',
                'PNB distinct du CA ; dette nette / EBE industriel non pertinente.',
                'BPA indicatif sur titres de clôture, pas moyenne pondérée auditée.']
            review(r, 'Fonds propres groupe rapprochés : 1 485,722 MMAD ; écart résiduel de 0,001 MMAD sur le contrôle total moins minoritaires.',
                'Tableau p.63 : 1485722 + 717 = 1486439 KMAD. Bilan p.58 : 1486440 - (18 + 699) = 1485723 KMAD. L’écart initial de 18 KMAD correspond aux réserves minoritaires affichées ; valeur publiée du tableau retenue avec réserve d’arrondi.')
        elif symbol == 'CDM':
            historical(r, 10881214, 24, 'Capital annuel 1088121400 MAD / nominal 100 ; somme de la répartition 10881214. Quotient RNPG annuel 863551000 / 10881214 = 79,36 MAD, cohérent CPC p.13.')
            r['reservations'] = [
                'BPA historique 2025 de 79,36 MAD, recoupé au CPC p.13 ; résumé de 79,44 non retenu.',
                'Capital porté à 11 626 499 titres en juillet 2026 : 10 881 214 + 745 285. PER, P/B et rendement au cours actuel non comparables sans ajustement documenté ; restent indisponibles.',
                'PNB distinct du CA. Semestre conservé sans annualisation.']
            review(r, 'BPA historique 2025 rétabli à 79,36 MAD ; PER et P/B au cours actuel restent indisponibles.',
                'CPC p.13 et capital annuel p.24 : 863551000 / 10881214. Communiqué du 28/07/2026 : +745285 titres, nouveau capital 1162649900 MAD / 100. Aucun mélange avec les comptes 2025.')
        elif symbol == 'HAL':
            if 'reconciliation_prior_annual' not in r:
                r['reconciliation_prior_annual'] = {k: copy.deepcopy(r[k]) for k in ('url', 'faits', 'provenance', 'reservations')}
            oldurl = r['url']
            for old in f.values():
                old.setdefault('url', oldurl)
            r.update(url=HAL_CONSO, pages_document=36, exercice_clos='2025-12-31', devise='MAD')
            r['provenance'] = dict(source_type='issuer_pdf', source_url=HAL_CONSO, document_hash=HASH_CONSO,
                reviewed_at='2026-10-05', validation_status='selected_pages_visually_checked_not_whole_report_certified',
                corroborating_documents=[dict(source_url=HAL_DR, document_hash=HASH_DR, pages='PDF p.200, 226-227, 236'), dict(source_url=HAL_CAP, document_hash=HASH_CAP, pages='PDF p.1')])
            for key, value, page, note in (
                ('resultat_net_part_groupe', 99.83237679, 6, '193474708.88 - 93642332.09 = 99832376.79 MAD ; bilan p.5, résultat global p.7 et opinion p.2 recoupent le RN consolidé sans minoritaires.'),
                ('capitaux_propres_part_groupe', 1445.97581836, 5, '502945280 + 251021566.80 + 592176594.77 + 99832376.79 = 1445975818.36 MAD.'),
                ('chiffre_affaires', 5911.76959127, 6, 'CA consolidé 5911769591.27 MAD, distinct des autres produits.'),
                ('chiffre_affaires_2024', 5022.14114061, 6, 'Comparatif même CPC et périmètre consolidé.')):
                f[key] = fact(r, value, page, note)
            f['excedent_brut_exploitation'] = fact(r, 525.676, 200,
                'EBE publié 525676 KMAD, distinct de l’EBITDA provisoire 541067. Recoupé au CPC : CA - achats - externes - personnel - impôts/taxes = 525676025.20 MAD, arrondi au KMAD.', url=HAL_DR, digest=HASH_DR)
            f['dettes_financieres'] = fact(r, 3504.407, 236,
                'KMAD arrondis : financement 1069960 + crédit-bail 313352 + trésorerie-passif 2121095 = 3504407. Exclut les obligations de personnel de 15820 KMAD détaillées p.226-227.', url=HAL_DR, digest=HASH_DR)
            f['tresorerie_actif'] = fact(r, 397.799, 236,
                '397799 KMAD arrondis ; dette nette 3504407 - 397799 = 3106608 KMAD, égale au tableau publié. Précision au KMAD, non au dirham.', url=HAL_DR, digest=HASH_DR)
            historical(r, 50294528, 5, 'Capital de clôture 502945280 MAD / nominal 10 ; CP septembre 2026 +3846050 => 54140578 titres actuels.', HAL_CONSO, HASH_CONSO)
            r['reservations'] = [
                'RNPG comptable 99,83237679 MMAD confirmé par les comptes consolidés complets ; bénéfice social/provisoire 104,436 non utilisé.',
                'EBE 525,676 MMAD, distinct de l’EBITDA 541,067. Dette financière 3504,407 et trésorerie 397,799 MMAD, arrondies au KMAD dans le document de référence ; obligations de personnel exclues. Dette nette 3106,608 MMAD.',
                'BPA historique indicatif sur 50 294 528 titres 2025 ; capital augmenté en septembre 2026 à 54 140 578. PER, P/B et rendement au cours actuel indisponibles sans ajustement comparable.']
            review(r, 'Résultat annuel confirmé ; EBE et dette nette rectifiés : 525,676 et 3 106,608 MMAD. BPA historique conservé, PER/P/B actuels bloqués.',
                'Comptes complets p.2, 5-7 ; document de référence p.200 et 236. Dette nette / EBE = 5,91, cohérent avec le 5,9 publié. Capital 2025 séparé de l’émission de septembre 2026. Ancien relevé archivé pour audit.')
        elif symbol == 'MGL':
            review(r, 'Fonds propres sociaux confirmés : 1 228,220 MMAD ; le graphique à 1 155 MMAD n’est pas utilisé.',
                'Bilan p.44 : 415158 + 138418 + 526445 + 148199 = 1228220 KMAD. Variation p.57 : 1153383 + 148199 - 73362 = 1228220 KMAD. Aucun changement des montants annuels déjà corrects.')
        elif symbol == 'M2M':
            recent = r.get('latest_report') or {}
            if recent.get('period_end') == '2026-06-30' and recent.get('document_url', '').endswith('/M2M_group_S1_26.pdf'):
                recent.update(reported_net_label='Résultat net consolidé total (minoritaires compris)',
                    reported_total_net_millions=recent['reported_net_millions'],
                    note='Synthèse p.1 : total consolidé, pas un RNPG isolé. Un BPA groupe négatif peut coexister avec un total positif si les minoritaires diffèrent : aucune contradiction prouvée. Aucun RNPG exact reconstruit à partir du BPA arrondi, aucun ratio semestriel dérivé.')
            r['strict_cash_unresolved'] = True
            r['reservations'] = ['La trésorerie annuelle importée inclut 144,0852 MMAD de valeurs mobilières de placement ; dette nette stricte suspendue tant que leur classification et les fonds de tiers ne sont pas rapprochés.']
            review(r, 'Présentation semestrielle corrigée : 8,780283 MMAD est le total consolidé, pas la part du groupe. RNPG S1 2026 non vérifié.',
                'Communiqué AMMC p.1 : total 8,780283 ; comparatif total 0,032371 ; BPA publié 10,64 et -0,70. Ces chiffres de périmètres différents ne prouvent pas une contradiction. Rapport complet requis pour isoler le RNPG ; ratios annuels non remplacés par le semestre.')
        if symbol not in ('HAL', 'M2M'):
            r['provenance']['reviewed_at'] = '2026-10-05'
    return out


if __name__ == '__main__':
    path = ROOT / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2) + '\n')
