"""Selected primary S1 2026 pages; preserve every existing semester on replay."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.ammc.ma/sites/default/files/'


def additions():
    rows = [
        ('MDP', 'Med_Paper_S1_26.pdf', '920bc778f0e04539db63e3f63e7f28429eba3a9ca15fa2a230d1fb8d6b9e8d01',
         'PDF p.1, synthèse comparative en KDH, recoupée au CPC p.2', 'Social, CGNC',
         0.950, 1.535, 39.015, 42.420, 'MAD',
         'Synthèse arrondie au KDH ; le CPC p.2 donne le total 2026 exact 949 967,74 MAD, pas 1 081 197,74 avant opérations précédentes. La colonne précédente du CPC porte l’annuel 2025 : le comparatif S1 provient exclusivement de la synthèse p.1.', 'CA'),
        ('STK', 'Stokvis_NA_S1_26.pdf', '686668d07b1e9773d964fab67f26bad4c1114c3eb9a6c4f4719bcaef73060a92',
         'PDF p.3, CPC consolidé en KMAD', 'Consolidé, normes nationales CNC, résultat part du groupe',
         -7.089, -0.323, 112.708, 107.617, 'MAD',
         'RNPG -7 089 et -323 KMAD ; totaux -7 090 et -325 exclus. Comptes sociaux p.2 distincts. L’attestation p.3 contient des réserves sur les filiales et une incertitude sur la continuité d’exploitation.', 'CA'),
        ('JET', 'Jet_Contractors_S1_26.pdf', 'e16321b5b72c3e91a11a6d54c7efee721ab2d35ec8bbef1146fe171ebf16c989',
         'PDF p.3, CPC consolidé en MAD ; synthèse p.1', 'Consolidé, résultat part groupe non réconcilié',
         None, None, 1772.53032745, 1460.30771735, 'MAD',
         'Résultat inutilisable : p.3 affiche 12 087 648,54 MAD au total XIII, 103 597 191,06 au total XVI (recoupé par CAC et synthèse), 107 525 818,90 en part groupe et 91 509 542,52 en minoritaires. Ces lignes ne se réconcilient pas. Aucun résultat total substitué au groupe ; aucun BPA/PER semestriel dérivé.', 'CA'),
        ('M2M', 'M2M_group_S1_26.pdf', 'f0d8aac22e85e906c99eba64a681f717b528c2f61b0c46b1290b74712058328a',
         'PDF p.1, synthèse consolidée en MAD', 'Consolidé, résultat total publié, part du groupe non isolée',
         8.780283, 0.032371, 82.914072, 60.739514, 'MAD',
         'Résultat net consolidé total de la synthèse, pas un RNPG validé. Le BPA comparatif publié -0,70 MAD ne concorde pas avec un quotient du total positif 32 371 MAD ; part groupe et dénominateurs non rapprochés, aucun ratio par action dérivé.', 'CA'),
        ('ENK', 'Ennakl_Automobiles_S1_26.pdf', '65b123df7247ccea02328f87c04320f39053c2c7287fc10a70ed98b854ee3a14',
         'PDF p.2, états consolidés IFRS en dinars tunisiens entiers', 'Consolidé IFRS, résultat part groupe ; comparatif 2025 retraité pro forma',
         29.973162, 37.140122, 368.370286, 352.118840, 'TND',
         'Millions TND, aucune conversion en MAD. RNPG explicitement publié 29 973 162 TND ; total 29 973 577, minoritaires 416 (écart d’arrondi 1 TND). Le semestre IFRS et son comparatif pro forma ne sont pas mélangés à l’annuel SCE 2025. Aucun ratio au cours MAD.', 'Produits issus des contrats avec les clients'),
        ('SAF', 'Sanlam_Maroc_S1_26.pdf', 'ef54e441e352f84bddc666d0236f314a48da3da2a3d1500451af33e21a87e6b9',
         'PDF p.4, CPC consolidé IFRS en KMAD ; périmètre p.1', 'Consolidé IFRS, résultat part groupe, Sanlam avant fusion Allianz',
         -88.608, 1177.155, 3687.110, 3019.420, 'MAD',
         'P.1 précise que tous les indicateurs concernent Sanlam avant fusion actée le 02/07/2026. Produits d’assurance IFRS 17, pas primes émises ni PNB. Perte RNPG -88 608 KMAD, comparative 1 177 155 ; aucune extrapolation ou donnée du groupe fusionné.', 'Produits d’assurance IFRS 17'),
    ]
    records = {}
    for symbol, filename, digest, pages, basis, net, previous, revenue, revenue_previous, currency, note, label in rows:
        url = BASE + filename
        records[symbol] = dict(semester_activity_label=label, latest_report=dict(
            period_end='2026-06-30', document_url=url, accounting_basis=basis, pages=pages,
            reported_net_millions=net, reported_net_previous_millions=previous,
            revenue_millions=revenue, revenue_previous_millions=revenue_previous,
            currency=currency, note=note, validation_status='pdf_page_visually_checked_2026-10-04',
            provenance=dict(source_type='regulator_pdf', source_url=url, document_hash='sha256:' + digest,
                reviewed_at='2026-10-04', validation_status='selected_pages_visually_checked_not_whole_report_certified')))
    url = 'https://evp-totalenergies-dam-prod-secured-cdn.wedia-group.com/medias/20260930-1750-43d7d49c-d0ca-41b4-a29c-835ff809b15f/compressed-pdf_output.pdf'
    records['TMA'] = dict(semester_activity_label='CA', latest_report=dict(
        period_end='2026-06-30', document_url=url,
        accounting_basis='Consolidé IFRS, résultat part du groupe',
        pages='PDF p.11, compte de résultat consolidé en milliers de MAD',
        reported_net_millions=284.955, reported_net_previous_millions=324.273,
        revenue_millions=8627.940, revenue_previous_millions=7543.580,
        currency='MAD', note='Rapport S1 2026 publié sur le site officiel TotalEnergies Marketing Maroc le 30/09/2026. RNPG explicitement isolé, égal au total. BPA semestriel arrondi publié 32 MAD non annualisé ; ratios annuels conservés.',
        validation_status='pdf_page_visually_checked_2026-10-04',
        provenance=dict(source_type='issuer_pdf', source_url=url,
            source_index='https://totalenergies.ma/total-au-maroc/espace-actionnaires/informations-reglementees',
            document_hash='sha256:dd3c7c6a7dab6030032bc25d60e59db2a9c35b45730031232b8c75665c3f2271',
            reviewed_at='2026-10-04', validation_status='selected_page_visually_checked_not_whole_report_certified')))
    return records


def merge(data):
    out = copy.deepcopy(data)
    for symbol, record in additions().items():
        target = out['records'].setdefault(symbol, {})
        if target.get('latest_report'):
            continue
        target.update(record)
    return out


if __name__ == '__main__':
    path = ROOT / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2) + '\n')
