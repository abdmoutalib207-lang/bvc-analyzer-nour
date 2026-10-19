"""One readable attribution space; canonical provenance stays in the data."""
from html import escape
from collections import Counter


def market_sources(report):
    overview = report.get('market_overview') or {}
    audit = report.get('cross_source_volume_audit') or {}
    groups = Counter(r.get('price_source') or 'Origine non renseignée' for r in report.get('results', []))
    rows = ''.join(f'<tr><td>{escape(name)}</td><td>{count} valeurs</td></tr>' for name,count in sorted(groups.items()))
    providers = ''.join(f'<li>{escape(p.get("provider") or "Fournisseur non renseigné")}</li>' for p in audit.get('providers', []))
    source = escape(overview.get('source') or 'Non renseignée')
    url = overview.get('source_url') or ''
    if url.startswith('https://'):
        source = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{source}</a>'
    return ('<section class="panel" id="marche"><span class="eyebrow">Provenance du marché</span>'
            '<h2>Cours, indices et contrôles</h2>'
            f'<p>MASI et bilan de séance : {source}. Séance {escape(str(overview.get("asof") or "non datée"))} · relevé {escape(str(overview.get("observed_at") or "non daté"))}.</p>'
            '<details><summary>Origine des cours par couverture</summary><div class="tablewrap"><table><thead><tr><th>Origine conservée</th><th>Couverture</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></details>'
            '<details><summary>Recoupement des volumes et mémoire des corrections</summary>'
            f'<ul>{providers}</ul><p>Montants recoupés : {"oui" if audit.get("cross_source_verified") else "non confirmés"} ; quantités : {"oui" if audit.get("quantities_cross_source_verified") else "non confirmées"}. '
            'Deux distributeurs peuvent partager un flux amont.</p>'
            '<a href="market-integrity.json">Preuves datées du rapprochement</a> · <a href="error-memory.json">Journal des erreurs et corrections</a></details>'
            '<p class="fineprint">Historique initial repris de l’archive du moteur principal, avec notamment des périodes Investing.com ; les origines détaillées et leurs dates sont conservées dans les exports et les dossiers des titres. Une attribution ne certifie pas les chiffres.</p></section>')
