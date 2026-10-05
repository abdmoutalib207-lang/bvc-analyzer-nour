"""JET S1 2026: reconcile the group result against the full issuer report."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://jet-contractors.com/documents/Rapport_Financier_s1_2026.pdf'
AMMC_URL = 'https://www.ammc.ma/sites/default/files/Jet_Contractors_S1_26.pdf'


def reference():
    return dict(
        period_end='2026-06-30', document_url=URL,
        accounting_basis='Consolidé, normes marocaines CNC, résultat net part du groupe',
        pages='PDF p.12, bilan passif et CPC en MAD ; p.15, commentaire du RNPG et du CA',
        reported_net_label='Résultat net part du groupe',
        reported_net_millions=91.50954252,
        reported_net_previous_millions=126.04480895,
        reported_net_previous_period_end='2025-06-30',
        reported_total_net_millions=103.59719106,
        reported_minority_net_millions=12.08764854,
        revenue_millions=1772.53032745,
        revenue_previous_millions=1460.30771735,
        currency='MAD',
        note=('RNPG retenu au bilan p.12 : 91 509 542,52 MAD, confirmé à 91,51 MDH '
              'dans le commentaire p.15. Minoritaires 12 087 648,54 MAD ; somme '
              '103 597 191,06 MAD, égale au total XVI et au résultat recalculé après impôt. '
              'Comparatif S1 2025 : RNPG 126 044 808,95 MAD au CPC p.12. '
              'Réserve : le CPC reprend les lignes erronées du communiqué '
              '(total XIII 12,09 MDH, minoritaires 91,51 MDH, part groupe 107,53 MDH) ; '
              'le commentaire p.15 comporte aussi une coquille sur l’année. '
              'Ces valeurs contradictoires ne sont pas utilisées. Le CA est distinct de la production. '
              'Aucun BPA/PER semestriel ni résultat annualisé dérivé.'),
        validation_status='selected_pages_reconciled_with_reservations_2026-10-05',
        provenance=dict(
            source_type='issuer_pdf', source_url=URL,
            document_hash='sha256:2e9545f2565811407ed0d2fe27bf20dcb770916eb0d23d249594c52568f4cf9d',
            reviewed_at='2026-10-05',
            validation_status='selected_pages_visually_checked_not_whole_report_certified',
            corroborating_documents=[dict(
                source_url=AMMC_URL, pages='PDF p.1 et p.3',
                document_hash='sha256:e16321b5b72c3e91a11a6d54c7efee721ab2d35ec8bbef1146fe171ebf16c989')],
            reconciliation_mad=dict(
                group_net=91509542.52, minority_net=12087648.54,
                total_net=103597191.06, previous_group_net=126044808.95,
                result_before_tax=167659709.31, equity_accounted_income=87852.29,
                goodwill_amortization=4766396.54, income_tax=59383974.00)))


def merge(data):
    out = copy.deepcopy(data)
    target = out['records']['JET']
    current = target.get('latest_report') or {}
    if str(current.get('period_end', '')) > '2026-06-30':
        return out
    if (current.get('period_end') != '2026-06-30'
            or current.get('document_url') not in (AMMC_URL, URL)):
        raise ValueError('JET: source ou période inattendue, nouvelle vérification requise')
    target['latest_report'] = reference()
    return out


if __name__ == '__main__':
    path = ROOT / 'data/facts_reference.json'
    path.write_text(json.dumps(merge(json.loads(path.read_text())), ensure_ascii=False, indent=2) + '\n')
