"""Readable per-issuer quote clocks; presentation never changes canonical facts."""
from datetime import date, datetime
from html import escape
from .bi_view import finite
from .collection_view import collection_stamp


def date_label(value):
    try:
        return date.fromisoformat(value).strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return 'date non communiquée'


def quote_view(item, record):
    price, session = item.get('price'), item.get('asof')
    source_time, collected = item.get('price_source_datetime'), item.get('price_collected_at')
    live = item.get('intraday_quote') or {}
    if item.get('resilience',{}).get('suspended',{}).get('market'):
        live = {}
    provisional = False
    try:
        provisional = (live.get('provisional') is True and finite(live.get('price'))
                       and live['price'] > 0 and date.fromisoformat(live['asof']) >= date.fromisoformat(session)
                       and item.get('intraday_status', 'provisional') == 'provisional')
    except (ValueError, TypeError, KeyError):
        pass
    bars = [b for b in (record.get('candles') or []) if isinstance(b,dict)]
    reference = None
    if provisional:
        price, session = live['price'], live['asof']
        source_time, collected = live.get('source_datetime'), item.get('intraday_observed_at')
        if item.get('asof') and item['asof'] < session:
            reference = (item.get('price'), item['asof'])
    elif len(bars) > 1 and bars[-1].get('d') == session:
        reference = (bars[-2].get('c'), bars[-2].get('d'))
    change = (100 * (price / reference[0] - 1)
              if reference and finite(price) and finite(reference[0]) and reference[0] > 0 else None)
    return {'price': price, 'session': session, 'provisional': provisional,
            'label': 'En séance · provisoire' if provisional else 'Clôture disponible' if finite(price) else 'Cours indisponible',
            'source_datetime': source_time, 'collected_at': collected,
            'source_checked_at': collected if provisional else item.get('source_checked_at'),
            'price_validated_at': item.get('price_validated_at'),
            'source_check_status': item.get('source_check_status'),
            'change_pct': change, 'reference_session': reference[1] if reference else None,
            'reference_price': reference[0] if reference else None}


def quote_clocks(view):
    try:
        day = date.fromisoformat(view.get('session'))
        day_text = day.strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        day=None;day_text='Date du cours non communiquée'
    try:
        stamp = datetime.strptime(view.get('source_datetime'), '%d/%m/%Y %H:%M:%S')
        if stamp.date() != day:
            raise ValueError('Different quote session')
        cotation = (f'<time datetime="{stamp.isoformat()}">{stamp:%d/%m/%Y} à {stamp:%Hh%M}</time>'
                    '<small>Heure indiquée par la source</small>')
    except (TypeError, ValueError):
        cotation = f'<time datetime="{escape(view.get("session") or "")}">{day_text}</time><small>Heure de cotation non communiquée</small>'
    return ('<div class="quote-clocks" data-quote-clocks><p class="quote-source-time">Cotation : '
            + cotation + '</p><div data-quote-collected>'
            + collection_stamp(view.get('collected_at'), 'Cours recueilli') + '</div>'
            + '<div data-title-source-check>' + (collection_stamp(view['source_checked_at'], 'Source contrôlée pour ce titre') if view.get('source_checked_at') else '<p>Dernier contrôle de source pour ce titre : heure non communiquée.</p>') + '</div>'
            + '<div data-title-validated>' + (collection_stamp(view['price_validated_at'], 'Dernière cotation validée') if view.get('price_validated_at') else '<p>Dernière cotation validée : heure non communiquée.</p>') + '</div></div>')
