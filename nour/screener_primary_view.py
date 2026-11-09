"""Dated findings from selected primary reviews, separate from the live comparison."""
from datetime import date
from html import escape


def review_note(review, asof):
    if not isinstance(review, dict):
        return ''
    try:
        reviewed = date.fromisoformat(review.get('reviewed_at', ''))
        if reviewed > date.fromisoformat(asof):
            return ''
    except (ValueError, TypeError):
        return ''
    findings = review.get('findings') or []
    conclusions = [item.get('conclusion') for item in findings if isinstance(item, dict)
                   and isinstance(item.get('conclusion'), str)]
    esc = lambda value: escape(str(value), quote=True)
    return ('<section class="panel" id="revue-primaire"><h2>Contrôles documentaires sélectionnés</h2>'
            f'<p>Revue du {esc(reviewed.isoformat())}. '
            'Les pages relues, les contrôles antérieurs et les corroborations de la Bourse sont distingués dans le relevé. '
            'Cette revue limitée ne certifie pas les autres chiffres du screener.</p><ul>'
            + ''.join('<li>' + esc(text) + '</li>' for text in conclusions)
            + '</ul><p><a href="screener-primary-review.json">Consulter les valeurs, pages, empreintes et limites de la revue</a></p></section>')
