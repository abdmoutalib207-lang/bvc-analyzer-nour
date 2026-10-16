"""Read-only BI presentation of existing financial outputs; no ratio calculation."""
import html
import math
from datetime import date
from urllib.parse import urlparse


def esc(value):
    return html.escape(str(value if value is not None else '—'), quote=True)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def number(value):
    return f'{value:,.2f}'.replace(',', ' ').replace('.', ',') if finite(value) else '—'


def financial_dashboard(item):
    f = item.get('fundamental') or {}
    bank = finite(f.get('pnb_mmad'))
    growth_key = 'pnb_growth_pct' if bank else 'revenue_growth_pct'
    metrics = [
        ('eps_mad', 'Bénéfice par action', 'MAD', 'valorisation', False,
         'La part du résultat annuel rapportée au nombre de titres retenu. Ce BPA peut être indicatif.',
         'Résultat annuel ÷ nombre de titres', f.get('eps_denominator')),
        ('pe', 'PER recalculé', '×', 'valorisation', False,
         'Le cours représente ce multiple du bénéfice annuel par action. Ce chiffre seul ne suffit pas à juger le prix.',
         'Cours daté ÷ BPA non arrondi', 'Le calcul utilise le BPA non arrondi, pas seulement les deux décimales affichées.'),
        ('pb', 'P/B recalculé', '×', 'valorisation', False,
         'Le cours est rapporté à la valeur comptable par action. Les différences de métier et de bilan comptent.',
         'Cours daté ÷ valeur comptable par action', f.get('book_denominator')),
        ('roe_pct', 'ROE', '%', 'rentabilite', True,
         'Le résultat annuel est rapporté aux fonds propres de clôture. Un signe négatif indique une perte sur cette base.',
         'Résultat annuel ÷ fonds propres de clôture × 100', f.get('roe_method')),
        (growth_key, 'Croissance du PNB' if bank else 'Croissance du CA', '%', 'rentabilite', True,
         'La variation annuelle de l’activité publiée, par rapport à l’exercice précédent. Elle ne mesure pas la croissance du bénéfice.',
         '(Activité annuelle ÷ activité annuelle précédente − 1) × 100', 'PNB bancaire ; distinct du chiffre d’affaires industriel.' if bank else 'Comparaison annuelle, sans annualisation du semestre.'),
        ('net_debt_strict_mmad', 'Dette nette stricte', 'MMAD', 'dette', False,
         'Le solde dépend du périmètre de dette et de trésorerie retenu. Un solde négatif ne garantit pas la disponibilité de tous les placements.',
         'Dette financière retenue − trésorerie retenue', f.get('net_debt_method')),
        ('net_debt_ebitda', 'Dette nette stricte / EBE', '×', 'dette', False,
         'La dette nette est rapportée à l’EBE annuel compatible. Ce multiple n’est pas une prévision de durée de remboursement.',
         'Dette nette stricte ÷ EBE annuel', f.get('net_debt_method')),
    ]
    if bank:
        metrics.insert(4, ('pnb_mmad', 'Produit net bancaire', 'MMAD', 'rentabilite', False,
            'L’activité bancaire nette publiée. Le PNB n’est ni le résultat net, ni le chiffre d’affaires d’une entreprise industrielle.',
            'Montant bancaire repris du document annuel', None))
    preferred = 'pe' if finite(f.get('pe')) else next((m[0] for m in metrics if finite(f.get(m[0]))), 'pe')
    cards, explanations = [], []
    for key, title, unit, group, directional, meaning, formula, method in metrics:
        value = f.get(key)
        known = finite(value)
        selected = key == preferred
        tone = 'missing' if not known else 'positive' if directional and value > 0 else 'negative' if directional and value < 0 else 'neutral'
        missing = 'Indisponible : donnée manquante, non comparable ou indicateur non applicable. Consulter les réserves ci-dessous.'
        if key.startswith('net_debt') and (f.get('debt_reconciliation') or {}).get('status') == 'unresolved':
            missing = 'Suspendu : dette à rapprocher. L’écart documentaire reste visible sous ce tableau.'
        elif key == 'pe' and finite(f.get('earnings_mmad')) and f['earnings_mmad'] <= 0:
            missing = 'PER non pertinent : le résultat annuel est nul ou négatif. Une perte publiée n’est pas une donnée manquante.'
        label = 'Valeur négative' if tone == 'negative' else 'Valeur positive' if tone == 'positive' else 'Indicateur descriptif' if known else 'Indisponible'
        if key == 'eps_mad' and f.get('historical_per_share_only'):
            title = f'BPA historique {f.get("exercise")}'
        cards.append(f'<button type="button" class="kpi fundamental-card bi-metric tone-{tone}" '
            f'data-bi-metric="{key}" data-bi-group="{group}" aria-pressed="{str(selected).lower()}" '
            f'aria-controls="bi-explain-{key}"><span>{esc(title)}</span><strong>{number(value)}</strong>'
            f'<small>{unit}</small><em>{label}</em></button>')
        period = f'Exercice {f.get("exercise") or "non documenté"} · clôture {f.get("period_end") or "non documentée"}'
        if key in ('pe', 'pb'):
            period += f' · cours au {item.get("asof") or "date non documentée"}'
        method_html = '<p class="fineprint">' + esc(method) + '</p>' if method else ''
        explanations.append(f'<details class="bi-explanation" id="bi-explain-{key}" '
            f'data-bi-explanation="{key}"{" open" if selected else ""}>'
            f'<summary>{esc(title)} · comprendre ce chiffre</summary><p class="bi-reading">{esc(meaning if known else missing)}</p>'
            f'<div class="bi-formula"><span>Méthode</span><p>{esc(formula)}</p></div>'
            f'{method_html}'
            f'<p class="fineprint">{esc(period)}.</p></details>')
    doc = str(f.get('document_url') or '')
    source = (f'<a href="{esc(doc)}" target="_blank" rel="noopener noreferrer">Ouvrir le document annuel ↗</a>'
              if urlparse(doc).scheme == 'https' else 'Document annuel non référencé')
    available = sum(finite(f.get(m[0])) for m in metrics)
    return ('<div class="bi-dashboard" data-bi-dashboard>'
        '<div class="bi-heading"><div><h3>Chiffres et lecture</h3>'
        '<p class="panel-sub">Sélectionnez un chiffre pour comprendre sa lecture.</p></div>'
        f'<span class="bi-count">{available} / {len(metrics)} indicateurs affichables</span></div>'
        '<div class="bi-filters" data-bi-filters hidden><label for="bi-group">Voir</label>'
        '<select id="bi-group"><option value="all">Tous les indicateurs</option>'
        '<option value="valorisation">Valorisation</option><option value="rentabilite">Activité et rentabilité</option>'
        '<option value="dette">Dette</option></select></div>'
        f'<div class="bi-layout"><div class="bi-cards">{"".join(cards)}</div>'
        f'<div class="bi-insight">{"".join(explanations)}<div class="bi-source">{source}</div></div></div>'
        '<p class="fineprint" data-bi-status role="status" aria-live="polite">Les absences restent affichées ; aucun chiffre n’est remplacé.</p></div>')


def semester_chart(recent):
    """Compare explicit, same-half-year RNPG amounts only, preserving signs."""
    current, previous = recent.get('reported_net_millions'), recent.get('reported_net_previous_millions')
    try:
        end = date.fromisoformat(recent.get('period_end', ''))
        prior = date.fromisoformat(recent.get('reported_net_previous_period_end', ''))
    except (TypeError, ValueError):
        return ''
    label = str(recent.get('reported_net_label', '')).lower()
    if (not all(finite(v) for v in (current, previous)) or recent.get('currency') != 'MAD'
            or end.month != 6 or end.day != 30 or prior.month != 6 or prior.day != 30
            or end.year != prior.year + 1 or not ('part' in label and 'groupe' in label)
            or not recent.get('accounting_basis')):
        return ''
    scale = max(abs(current), abs(previous)) or 1
    bars = []
    for period, value in ((prior, previous), (end, current)):
        width = 50 * abs(value) / scale
        left = 50 - width if value < 0 else 50
        bars.append(f'<div class="bi-bar-row"><span>{period.isoformat()}</span>'
            f'<div class="bi-bar-track" aria-hidden="true"><i class="{"loss" if value < 0 else "gain"}" '
            f'style="left:{left:.3f}%;width:{width:.3f}%"></i></div><strong>{number(value)}</strong></div>')
    return ('<figure class="bi-comparison"><figcaption>Résultat semestriel part du groupe · MMAD</figcaption>'
            + ''.join(bars) + '<p class="fineprint">Même semestre, comparatif repris du document ; axe à zéro au centre. Aucun semestre annualisé.</p></figure>')
