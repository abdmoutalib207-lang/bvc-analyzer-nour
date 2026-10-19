"""Render an observed collection time without substituting the build time."""
from datetime import datetime
from html import escape
from .runtime import ZONE


def collection_stamp(value, label='Relevé collecté'):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('Timezone required')
        local = parsed.astimezone(ZONE)
    except (AttributeError, TypeError, ValueError):
        return '<p class="collection-stamp">Heure de collecte non communiquée.</p>'
    return (f'<p class="collection-stamp">{escape(label)} : '
            f'<time datetime="{escape(local.isoformat(), quote=True)}">'
            f'{local:%d/%m/%Y} à {local:%Hh%M} (Casablanca)</time></p>')
