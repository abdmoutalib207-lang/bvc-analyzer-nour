"""Dated user-supplied market aggregates, separate from per-equity candles."""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
import re

MARKETS = {'Marché central', 'Transferts', 'Augmentation capital numéraire', 'Apports titres'}


def checked_history(document):
    """Fail closed on malformed imports; never merge market segments."""
    if document.get('schema_version') != 1:
        raise ValueError('Version historique inconnue')
    source = document.get('source', {})
    if (source.get('status') != 'user_supplied_export_reviewed'
            or not re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', ''))
            or source.get('sheet') != 'in'):
        raise ValueError('Provenance historique incomplète')
    seen = set()
    for row in document.get('records', []):
        try:
            date.fromisoformat(row['session'])
            key = (row['session'], row['market'])
            if row['market'] not in MARKETS or key in seen:
                raise ValueError('Marché inconnu ou séance/marché dupliqué')
            seen.add(key)
            amount = Decimal(row['turnover_mad'])
            if (not isinstance(row['turnover_mad'], str) or not amount.is_finite()
                    or amount < 0 or amount != amount.quantize(Decimal('.01'))):
                raise ValueError('Montant invalide')
            for field in ('transactions', 'shares', 'row'):
                if type(row[field]) is not int or row[field] < (2 if field == 'row' else 0):
                    raise ValueError('Compteur ou ligne invalide')
        except (KeyError, TypeError, InvalidOperation) as exc:
            raise ValueError('Ligne historique invalide') from exc
    if not seen:
        raise ValueError('Historique vide')
    return deepcopy(document)


def compare_current(document, overview):
    """Compare only the exact central-market session; no date fallback."""
    document = checked_history(document)
    row = next((r for r in document['records'] if r['session'] == overview.get('asof')
                and r['market'] == 'Marché central'), None)
    result = {'status': 'not_covered', 'session': overview.get('asof'),
              'source_status': document['source']['status'], 'reference_url': 'historique-volumes.html'}
    if row is None:
        return result
    differences = {}
    for field in ('turnover_mad', 'shares'):
        actual = overview.get(field)
        try:
            matches = (not isinstance(actual, bool) and actual is not None
                       and Decimal(str(actual)) == Decimal(str(row[field])))
        except InvalidOperation:
            matches = False
        if not matches:
            differences[field] = {'observed': actual, 'export': row[field]}
    reported = overview.get('transactions_reported', overview.get('transactions'))
    if reported != row['transactions']:
        differences['transactions'] = {'observed': reported, 'export': row['transactions']}
    result.update(status='difference' if differences else 'matched', reference=row,
                  differences=differences, source_sha256=document['source']['sha256'],
                  notice='Export fourni par l’utilisateur, relu ; aucune collecte officielle automatique attestée. '
                         'Ce rapprochement ne valide pas la décomposition par titre et ne remplace aucune bougie.')
    return result


def history_page(document, comparison):
    from .site import shell
    document = checked_history(document)
    rows = sorted(document['records'], key=lambda r: r['row'])
    def number(value):
        return format(Decimal(str(value)), ',f').replace(',', ' ').replace('.', ',')
    body = ''.join('<tr>' + ''.join(f'<td>{escape(str(v))}</td>' for v in
                   (r['session'], r['market'], number(r['turnover_mad']), number(r['transactions']),
                    number(r['shares']), f"in!A{r['row']}:E{r['row']}")) + '</tr>' for r in rows)
    latest = comparison.get('reference')
    notice = (f"Export daté du {latest['session']} : {number(latest['transactions'])} transactions sur le marché central. "
              'Les divergences avec les compteurs fournisseurs restent conservées dans le contrôle.' if latest
              else 'La séance courante n’est pas couverte par cet export ; aucune ancienne ligne ne la remplace.')
    sessions = len({r['session'] for r in rows})
    page_body = ('<link rel="stylesheet" href="nour.css">'
            '<style>table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}'
            'th,td{padding:12px;text-align:left;border-bottom:1px solid #284046;white-space:nowrap}'
            'thead{background:#143737}caption{text-align:left;padding:12px 0;color:#adc2c0}'
            'code{overflow-wrap:anywhere}p{line-height:1.6}a{color:#b4e283}</style>'
            '<main style="max-width:1200px;margin:2rem auto;padding:1rem"><a href="index.html">← Marché Nour</a>'
            f'<h1>Historique des volumes</h1><p>{sessions} séances · export documentaire fourni par l’utilisateur, relu. '
            'Marché central, transferts et opérations sur capital restent séparés.</p>'
            f'<p>{escape(notice)}</p><p>Ces agrégats ne constituent pas un historique de cours par titre. '
            'L’export ne démontre ni une collecte officielle automatique ni le rapprochement de chaque instrument.</p>'
            '<div style="overflow-x:auto"><table><caption>Montants en MAD ; compteurs selon les colonnes de l’export</caption>'
            '<thead><tr><th>Séance</th><th>Marché</th><th>Volume (MAD)</th><th>Transactions</th><th>Titres échangés</th><th>Ligne source</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div><p><a href="volume-history.json">Données et provenance</a> · '
            '<a href="volume-history-check.json">Contrôle de la séance courante</a></p>'
            f'<p>Empreinte SHA-256 du fichier original : <code>{document["source"]["sha256"]}</code>.</p></main>')
    return shell('Historique des volumes',page_body,'','')
