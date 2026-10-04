"""Attributed annual facts: currency, denominator and period are explicit contracts."""
import math
from urllib.parse import urlparse


def calculate(record, facts):
    out = dict(source='absent', exercise=None, document_url=None, evidence={},
               eps_mad=None, book_value_per_share_mad=None, pe=None, pb=None,
               revenue_growth_pct=None, roe_pct=None, dividend_yield_pct=None,
               earnings_mmad=None, warnings=[], accounting_basis=None,
               currency=None, net_debt_strict_mmad=None, net_debt_ebitda=None,
               calculation_version='nour-fundamentals-v2', point_in_time_ready=False,
               roe_method='Résultat annuel / capitaux propres de clôture, non moyens',
               pnb_mmad=None, pnb_growth_pct=None,
               validation_status='missing', provenance={}, latest_report=None)
    if isinstance(facts, dict):
        out.update(latest_report=facts.get('latest_report'), provenance=facts.get('provenance',{}))
    if not isinstance(facts, dict) or urlparse(str(facts.get('url') or '')).scheme != 'https':
        return out
    out.update(source='relevé documentaire référencé, non certifié par cet import',
               exercise=facts.get('exercice'), document_url=facts['url'],
               accounting_basis=facts.get('accounting_basis'),
               currency=facts.get('devise', 'MAD'), provenance=facts.get('provenance', {}),
               validation_status='referenced_import', latest_report=facts.get('latest_report'),
               period_end=facts.get('exercice_clos') or f"{facts.get('exercice')}-12-31")
    out['warnings'].extend(facts.get('reservations') or [])
    if facts.get('provenance', {}).get('source_type') == 'regulator_pdf':
        out['source'] = 'Pages sélectionnées du PDF primaire contrôlées visuellement ; rapport non certifié par Nour'
        out['validation_status'] = facts['provenance'].get('validation_status')
    data = facts.get('faits') or {}
    def fact(key):
        f = data.get(key) or {}
        v, page = f.get('valeur'), f.get('page')
        if (isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v)
                or isinstance(page, bool) or not isinstance(page,int) or page < 1):
            return None
        if f.get('devise', out['currency']) != 'MAD':
            return None
        out['evidence'][key] = dict(value=v, page=page, unit=f.get('unite','MMAD'),
            document_url=f.get('url') or facts['url'], note=f.get('note',''),
            accounting_basis=f.get('base') or out['accounting_basis'],
            original_unit=f.get('unite_au_rapport'),
            document_hash=f.get('document_hash'), printed_page=f.get('printed_page'),
            validation_status=f.get('validation_status','referenced_import'))
        return float(v)
    if out['currency'] != 'MAD':
        out['warnings'].append('Devise étrangère : aucun ratio au cours MAD sans conversion documentée.')
        return out
    net = fact('resultat_net_part_groupe')
    equity = fact('capitaux_propres_part_groupe')
    # Never silently substitute the consolidated total (including minorities).
    # Social-only accounts require explicitly sourced social keys.
    if net is None:
        net = fact('resultat_net_social')
    if equity is None:
        equity = fact('capitaux_propres_sociaux')
    weighted = fact('nombre_actions_retenu_pour_le_bpa')
    existing = fact('nombre_actions_existant')
    ordinary = fact('nombre_actions') or fact('nombre_actions_au_rapport')
    eps_shares = weighted or ordinary
    book_shares = existing or ordinary
    out['eps_denominator'] = 'moyenne pondérée publiée' if weighted else 'nombre de titres référencé ; BPA indicatif'
    out['book_denominator'] = 'titres existants référencés' if existing else 'nombre de titres référencé'
    # Known capital changes: current capital / old equity must not masquerade
    # as a current audited book value. Keep the inputs but withhold per-share ratios.
    if facts.get('capital_change_unresolved'):
        eps_shares = book_shares = None
        out['warnings'].append('Variation du capital : rapprochement des dénominateurs requis ; BPA, PER et P/B retenus indisponibles.')
    revenue = fact('chiffre_affaires')
    previous = fact(f"chiffre_affaires_{(facts.get('exercice') or 0)-1}")
    dividend = fact('dividende_par_action')
    price = record.get('price')
    price = float(price) if isinstance(price,(int,float)) and not isinstance(price,bool) and math.isfinite(price) and price>0 else None
    eps = net*1e6/eps_shares if net is not None and eps_shares and eps_shares>0 else None
    book = equity*1e6/book_shares if equity is not None and book_shares and book_shares>0 else None
    rnd = lambda x: round(x,2) if x is not None and math.isfinite(x) else None
    out.update(eps_mad=rnd(eps), book_value_per_share_mad=rnd(book), earnings_mmad=net,
               pe=rnd(price/eps) if price and eps and eps>0 else None,
               pb=rnd(price/book) if price and book and book>0 else None,
               roe_pct=rnd(net/equity*100) if net is not None and equity and equity>0 else None,
               revenue_growth_pct=rnd((revenue/previous-1)*100) if revenue is not None and previous and previous>0 else None,
               dividend_yield_pct=rnd(dividend/price*100) if dividend is not None and price else None)
    pnb, pnb_previous = fact('produit_net_bancaire'), fact(f"produit_net_bancaire_{(facts.get('exercice') or 0)-1}")
    out['pnb_mmad'] = rnd(pnb)
    out['pnb_growth_pct'] = rnd((pnb/pnb_previous-1)*100) if pnb is not None and pnb_previous and pnb_previous>0 else None
    debt, cash, ebitda = fact('dettes_financieres'), fact('tresorerie_actif'), fact('excedent_brut_exploitation')
    strict = debt-cash if debt is not None and cash is not None else None
    out['net_debt_strict_mmad'] = rnd(strict)
    out['net_debt_ebitda'] = rnd(strict/ebitda) if strict is not None and ebitda and ebitda>0 else None
    out['net_debt_method'] = 'Dette financière moins trésorerie-actif ; hors placements et comptes associés. Non comparable sans périmètre identique.'
    if facts.get('financial_business'):
        out['net_debt_strict_mmad'] = out['net_debt_ebitda'] = None
        out['net_debt_method'] = 'Non calculé pour cet établissement financier : dette nette / EBE industriel non comparable.'
    metrics = ('eps_mad','pb','roe_pct','revenue_growth_pct')
    out['coverage_pct'] = 25*sum(out[k] is not None for k in metrics)
    out['missing_metrics'] = [k for k in metrics if out[k] is None]
    return out


def coverage(results):
    """Universe coverage is not the percentage of certified reports."""
    return dict(universe=len(results), referenced=sum(bool(r['fundamental']['document_url']) for r in results),
                with_eps=sum(r['fundamental']['eps_mad'] is not None for r in results),
                with_pb=sum(r['fundamental']['pb'] is not None for r in results),
                with_roe=sum(r['fundamental']['roe_pct'] is not None for r in results),
        with_recent_report=sum(bool(r['fundamental'].get('latest_report')) for r in results),
                missing_documents=[r['symbol'] for r in results if not r['fundamental']['document_url']],
                interpretation='Couverture de relevés sourcés ; pas une certification ni une probabilité de rendement.')
