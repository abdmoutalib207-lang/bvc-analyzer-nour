"""Versioned descriptive business calculations, isolated from the canonical score.

Formulas are operational; a value requires primary-checked compatible inputs.
Definitions describe issuer disclosures, never manufacture a business KPI.
"""
from datetime import date
from decimal import Decimal, localcontext
import math
import re
from urllib.parse import urlsplit

from .sector_methods import guidance
from .financial_audit import REVIEWED, _basis

VERSION = 'nour-sector-calculators-v2'
# Same-currency monetary ratios are invariant to the currency scale. This is
# deliberately narrower than FX support: amounts and MAD/physical outputs must
# not acquire a foreign value under a MAD-labelled key.
MONETARY_UNITS = {'MAD': 'MMAD', 'TND': 'MTND'}
NATIVE_MONETARY_RATIOS = frozenset({
    'operating_margin_pct', 'group_margin_pct', 'ebe_margin_pct',
    'ebitda_margin_pct', 'capex_revenue_pct', 'operating_cash_margin_pct',
    'working_capital_revenue_pct', 'asset_turnover', 'inventory_turnover',
    'roic_pct', 'cost_income_pct', 'cost_risk_average_loans_pct',
    'npl_ratio_pct', 'npl_coverage_pct', 'capital_adequacy_pct',
    'loss_ratio_pct', 'expense_ratio_pct', 'combined_ratio_pct',
    'insurance_solvency_coverage_pct', 'client_concentration_pct',
    'recurring_revenue_pct', 'epra_ltv_pct',
    'native_group_roe_closing_pct', 'native_group_roe_average_pct',
})
REFERENCES = {
 'cfa':'https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/financial-analysis-techniques',
 'institutions':'https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/analysis-of-financial-institutions',
 'damodaran':'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/definitions.html',
 'bam':'https://www.bkam.ma/content/download/847887/9165409/Rapport%20DSB%202025.pdf',
 'acaps':'https://www.acaps.ma/sites/default/files/2026-02/ACAPS_Rapport%20Secteur%20assurance%202024.pdf',
 'epra':'https://www.epra.com/finance/guidelines',
 'ias33':'https://www.ifrs.org/issued-standards/list-of-standards/ias-33-earnings-per-share/',
 'ias34':'https://www.ifrs.org/content/dam/ifrs/publications/html-standards/english/2026/issued/ias34.html',
 'ifrs8':'https://www.ifrs.org/issued-standards/list-of-standards/ifrs-8-operating-segments/',
}


def rule(label, inputs, expression, unit='%', reference='cfa', note='', contract=None):
    return dict(label=label, inputs=inputs, expression=expression, unit=unit,
                reference=reference, note=note, definition_contract=contract)


# Explicit operations, no eval or executable expression from a document.
RULES = {
 'native_group_roe_closing_pct':rule('ROE groupe de clôture en devise native', ['resultat_net_part_groupe','capitaux_propres_groupe_cloture'],'ratio100',note='ROE descriptif hors score ; aucun montant ni multiple au cours MAD déduit.'),
 'native_group_roe_average_pct':rule('ROE groupe sur capitaux propres moyens en devise native', ['resultat_net_part_groupe','capitaux_propres_groupe_ouverture','capitaux_propres_groupe_cloture'],'ratio_average100',note='Deux capitaux propres attribuables positifs et compatibles ; hors score, sans conversion FX.'),
 'operating_margin_pct':rule('Marge opérationnelle', ['resultat_exploitation','chiffre_affaires'],'ratio100'),
 'group_margin_pct':rule('RNPG / chiffre d’affaires', ['resultat_net_part_groupe','chiffre_affaires'],'ratio100',note='Part groupe explicitement distinguée de la marge nette consolidée totale.'),
 'ebe_margin_pct':rule('Marge d’EBE publié', ['excedent_brut_exploitation','chiffre_affaires'],'ratio100',note='EBE publié, jamais automatiquement assimilé à un EBITDA IFRS.'),
 'ebitda_margin_pct':rule('Marge EBITDA publié', ['ebitda_publie','chiffre_affaires'],'ratio100',note='Exige un EBITDA publié et sa définition ; aucun ajout arbitraire de provisions.',contract='issuer_defined_ebitda'),
 'capex_revenue_pct':rule('CAPEX décaissé / CA', ['capex_decaisse','chiffre_affaires'],'ratio100',note='CAPEX positif décaissé ; acquisitions de sociétés distinctes.'),
 'operating_cash_margin_pct':rule('Flux opérationnel / CA', ['flux_tresorerie_exploitation','chiffre_affaires'],'ratio100'),
 'free_cash_after_capex_mmad':rule('Flux opérationnel moins CAPEX décaissé', ['flux_tresorerie_exploitation','capex_decaisse'],'subtract',unit='MMAD',reference='damodaran',note='Solde après CAPEX, pas FCFE ni FCFF normalisé.'),
 'operating_working_capital_mmad':rule('BFR d’exploitation', ['stocks','creances_exploitation','dettes_exploitation'],'working_capital',unit='MMAD',reference='damodaran',note='Hors trésorerie et financement ; postes d’exploitation homogènes.'),
 'working_capital_revenue_pct':rule('BFR d’exploitation / CA', ['stocks','creances_exploitation','dettes_exploitation','chiffre_affaires'],'working_capital_ratio'),
 'asset_turnover':rule('Rotation des actifs moyens', ['chiffre_affaires','actif_total_ouverture','actif_total_cloture'],'ratio_average',unit='×'),
 'inventory_turnover':rule('Rotation des stocks moyens', ['cout_des_ventes','stocks_ouverture','stocks_cloture'],'ratio_average',unit='×'),
 'roic_pct':rule('ROIC sur capital investi moyen', ['nopat_documente','capital_investi_ouverture','capital_investi_cloture'],'ratio_average100',reference='damodaran',contract='same_operating_invested_capital',note='NOPAT et capital investi documentés ; aucun taux fiscal universel supposé.'),
 'cost_income_pct':rule('Coefficient d’exploitation bancaire', ['charges_generales_exploitation','produit_net_bancaire'],'ratio100',reference='bam',contract='bank_cost_income',note='Charges hors coût du risque ; même base bancaire que le PNB.'),
 'cost_risk_average_loans_pct':rule('Coût du risque / crédits bruts moyens', ['cout_du_risque','credits_bruts_ouverture','credits_bruts_cloture'],'ratio_average100',reference='bam',contract='bank_gross_customer_loans',note='Non annualisé ; dénominateur explicite, distinct du coût du risque / RBE.'),
 'npl_ratio_pct':rule('Créances en souffrance / crédits bruts', ['creances_en_souffrance','credits_bruts_cloture'],'ratio100',reference='bam',contract='bank_gross_customer_loans'),
 'npl_coverage_pct':rule('Couverture des créances en souffrance', ['provisions_sur_creances_en_souffrance','creances_en_souffrance'],'ratio100',reference='bam',contract='bank_npl_provisions'),
 'capital_adequacy_pct':rule('Solvabilité bancaire réglementaire', ['fonds_propres_reglementaires','actifs_ponderes_risques'],'ratio100',reference='bam',contract='bank_regulatory_capital',note='Fonds propres réglementaires, pas capitaux propres comptables.'),
 'loss_ratio_pct':rule('Sinistralité non-vie', ['sinistres_survenus_non_vie','primes_acquises_non_vie'],'ratio100',reference='acaps',contract='nonlife_same_reinsurance_basis'),
 'expense_ratio_pct':rule('Chargement non-vie', ['frais_techniques_non_vie','primes_acquises_non_vie'],'ratio100',reference='acaps',contract='nonlife_same_reinsurance_basis'),
 'combined_ratio_pct':rule('Ratio combiné non-vie', ['sinistres_survenus_non_vie','frais_techniques_non_vie','primes_acquises_non_vie'],'sum_ratio100',reference='acaps',contract='nonlife_same_reinsurance_basis',note='Ne mélange pas primes locales et revenus IFRS 17 ; base de réassurance identique.'),
 'insurance_solvency_coverage_pct':rule('Couverture de la marge de solvabilité', ['fonds_admis_solvabilite','marge_solvabilite_requise'],'ratio100',reference='acaps',contract='acaps_solvency_margin',note='Pas un SCR Solvabilité II déduit des capitaux propres.'),
 'backlog_revenue_years':rule('Carnet / CA annuel', ['carnet_commandes','chiffre_affaires'],'ratio',unit='années',note='Couverture indicative du CA ; ni délai certain ni bénéfice futur.'),
 'book_to_bill':rule('Commandes nouvelles / CA', ['commandes_nouvelles','chiffre_affaires'],'ratio',unit='×'),
 'recurring_revenue_pct':rule('Part des revenus récurrents publiés', ['revenus_recurrents','chiffre_affaires'],'ratio100',contract='documented_recurring_revenue',note='Aucun ARR, MRR ou SaaS supposé.'),
 'client_concentration_pct':rule('CA du premier client / CA', ['ca_premier_client','chiffre_affaires'],'ratio100'),
 'epra_vacancy_pct':rule('Vacance EPRA en loyers potentiels', ['loyer_marche_surfaces_vacantes','loyer_marche_portefeuille'],'ratio100',reference='epra',contract='epra_vacancy_erv',note='Loyers potentiels homogènes, pas surfaces seules.'),
 'epra_ltv_pct':rule('EPRA LTV', ['epra_dette_nette_ajustee','epra_valeur_immobiliere_ajustee'],'ratio100',reference='epra',contract='epra_ltv_reconciled',note='Rapprochement EPRA exigé ; dette bancaire / immeubles n’est pas automatiquement EPRA LTV.'),
 'hotel_occupancy_pct':rule('Occupation hôtelière', ['nuitees_chambres_vendues','nuitees_chambres_disponibles'],'ratio100',unit='%',contract='hotel_room_nights'),
 'hotel_adr_mad':rule('Prix moyen des chambres', ['revenu_chambres_mad','nuitees_chambres_vendues'],'ratio',unit='MAD/chambre',contract='hotel_room_nights'),
 'hotel_revpar_mad':rule('RevPAR', ['revenu_chambres_mad','nuitees_chambres_disponibles'],'ratio',unit='MAD/chambre',contract='hotel_room_nights'),
 'mine_unit_cost':rule('Coût de production / unité produite', ['cout_production_mad','production_miniere'],'ratio',unit='MAD/unité',contract='same_metal_saleable_unit',note='Même métal, unité et périmètre ; pas de cash-cost/AISC recomposé.'),
 'port_utilization_pct':rule('Utilisation de capacité portuaire', ['trafic_portuaire','capacite_portuaire'],'ratio100',contract='same_port_capacity_unit',note='EVP et tonnes ne sont pas interchangeables.'),
 'electric_capacity_factor_pct':rule('Facteur de charge électrique', ['production_mwh','capacite_mw','heures_periode'],'capacity_factor',contract='same_generation_scope'),
}

COMMON = ('operating_margin_pct','group_margin_pct','ebe_margin_pct','ebitda_margin_pct',
          'capex_revenue_pct','operating_cash_margin_pct','free_cash_after_capex_mmad',
          'operating_working_capital_mmad','working_capital_revenue_pct','asset_turnover','roic_pct')
FINANCIAL = {'Banque','Assurance','Finance - crédit-bail','Finance - crédit à la consommation','Crédit à la consommation'}
BY_FAMILY = {
 'Banque':('cost_income_pct','cost_risk_average_loans_pct','npl_ratio_pct','npl_coverage_pct','capital_adequacy_pct'),
 'Finance - crédit-bail':('cost_income_pct','cost_risk_average_loans_pct','npl_ratio_pct','npl_coverage_pct','capital_adequacy_pct'),
 'Finance - crédit à la consommation':('cost_income_pct','cost_risk_average_loans_pct','npl_ratio_pct','npl_coverage_pct','capital_adequacy_pct'),
 'Assurance':('loss_ratio_pct','expense_ratio_pct','combined_ratio_pct','insurance_solvency_coverage_pct'),
 'Immobilier - foncières':('epra_vacancy_pct','epra_ltv_pct'),
 'BTP et ingénierie':('backlog_revenue_years','book_to_bill'),
 'Industrie - équipements et métallurgie':('backlog_revenue_years','book_to_bill'),
 'Technologie et services':('recurring_revenue_pct','client_concentration_pct'),
 'Services informatiques et logiciels':('recurring_revenue_pct','client_concentration_pct'),
 'Télécommunications':('recurring_revenue_pct','client_concentration_pct'),
 'Tourisme et hôtellerie':('hotel_occupancy_pct','hotel_adr_mad','hotel_revpar_mad'),
 'Mines':('mine_unit_cost',), 'Ports et logistique':('port_utilization_pct',),
 'Production électrique':('electric_capacity_factor_pct',),
 'Grande distribution':('inventory_turnover',),
 'Distribution informatique':('inventory_turnover','client_concentration_pct'),
 'Distribution automobile':('inventory_turnover',),
}
# Direct business disclosures, never inferred from an industrial revenue proxy.
PUBLISHED_KPIS={
 'Banque':{'produit_net_bancaire':('PNB','MMAD'),'cout_du_risque':('Coût du risque','MMAD'),'creances_en_souffrance':('Créances en souffrance','MMAD')},
 'Assurance':{'primes_emises':('Primes émises','MMAD'),'resultat_technique':('Résultat technique','MMAD')},
 'Immobilier - promotion':{'preventes':('Préventes documentées','MMAD'),'livraisons':('Unités livrées','unites'),'stocks':('Stocks','MMAD'),'encaissements_clients':('Encaissements clients','MMAD')},
 'Immobilier - foncières':{'revenus_locatifs':('Revenus locatifs','MMAD'),'ffo_publie':('FFO selon définition publiée','MMAD')},
 'BTP et ingénierie':{'carnet_commandes':('Carnet de commandes','MMAD'),'commandes_nouvelles':('Commandes nouvelles','MMAD'),'avancement_projets_pct':('Avancement documenté des projets','%')},
 'Mines':{'production_miniere':('Production minière et unité métallique publiée','unites'),'cout_production_mad':('Coûts de production','MAD'),'capex_decaisse':('CAPEX décaissé','MMAD')},
 'Télécommunications':{'arpu_mad_mois':('ARPU, périmètre et période de facturation documentés','MAD/abonne/mois'),'revenus_recurrents':('Revenus récurrents publiés','MMAD')},
 'Technologie et services':{'revenus_recurrents':('Revenus récurrents publiés','MMAD'),'ca_premier_client':('CA du premier client','MMAD')},
 'Services informatiques et logiciels':{'revenus_recurrents':('Revenus récurrents publiés','MMAD'),'ca_premier_client':('CA du premier client','MMAD')},
 'Santé - hôpitaux':{'lits_operationnels':('Lits opérationnels','unites'),'taux_occupation_lits_pct':('Occupation des lits','%')},
 'Agriculture et intrants':{'volumes_vendus':('Volumes vendus, unité publiée','unites')},
 'Ports et logistique':{'trafic_portuaire':('Trafic et unité publiée','unites')},
 'Production électrique':{'production_mwh':('Production électrique','MWh'),'capacite_mw':('Capacité de production','MW')},
 'Tourisme et hôtellerie':{'nuitees_chambres_vendues':('Nuitées chambres vendues','chambres')},
}
BY_FAMILY['Crédit à la consommation']=BY_FAMILY['Finance - crédit à la consommation']


def published_kpis(data,family,period,asof):
    out={}
    for field,(label,unit) in PUBLISHED_KPIS.get(family,{}).items():
        fact=data.get(field);valid=False
        if isinstance(fact,dict):
            value=fact.get('valeur')
            try:
                valid=(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
                    and fact.get('unite')==unit and fact.get('devise','MAD')=='MAD'
                    and fact.get('validation_status') in REVIEWED and fact.get('period_end')==period
                    and period<=asof and bool(fact.get('base'))
                    and isinstance(fact.get('page'),int) and not isinstance(fact['page'],bool) and fact['page']>0
                    and re.fullmatch(r'sha256:[0-9a-f]{64}',str(fact.get('document_hash','')))
                    and urlsplit(str(fact.get('url',''))).scheme=='https')
            except (TypeError,ValueError,OverflowError):valid=False
        out[field]=dict(label=label,value=fact['valeur'] if valid else None,unit=unit,
            status='primary_page_checked' if valid else 'unavailable',source=fact,
            reason=None if valid else 'Donnée métier primaire ou définition/unité compatible non vérifiée.',
            used_for_score=False,certified=False)
    return out


def formula_text(spec):
    v=spec['inputs']; op=spec['expression']
    if op in ('ratio','ratio100'): return ('100 × ' if op=='ratio100' else '')+f'{v[0]} / {v[1]}'
    if op in ('ratio_average','ratio_average100'):return ('100 × ' if op.endswith('100') else '')+f'{v[0]} / moyenne({v[1]}, {v[2]})'
    if op=='subtract':return f'{v[0]} − {v[1]}'
    if op=='working_capital':return f'{v[0]} + {v[1]} − {v[2]}'
    if op=='working_capital_ratio':return f'100 × ({v[0]} + {v[1]} − {v[2]}) / {v[3]}'
    if op=='sum_ratio100':return f'100 × ({v[0]} + {v[1]}) / {v[2]}'
    return f'100 × {v[0]} / ({v[1]} × {v[2]})'


def _compute(operation, v):
    if operation in ('ratio','ratio100'):
        if v[1] <= 0: raise ValueError('Dénominateur non positif')
        return v[0]/v[1]*(100 if operation.endswith('100') else 1)
    if operation in ('ratio_average','ratio_average100'):
        if v[1] <= 0 or v[2] <= 0: raise ValueError('Deux dénominateurs moyens positifs requis')
        return 2*v[0]/(v[1]+v[2])*(100 if operation.endswith('100') else 1)
    if operation == 'subtract': return v[0]-v[1]
    if operation == 'working_capital': return v[0]+v[1]-v[2]
    if operation == 'working_capital_ratio':
        if v[3] <= 0: raise ValueError('CA non positif')
        return 100*(v[0]+v[1]-v[2])/v[3]
    if operation == 'sum_ratio100':
        if v[2] <= 0: raise ValueError('Primes acquises non positives')
        return 100*(v[0]+v[1])/v[2]
    if operation == 'capacity_factor':
        if v[1] <= 0 or v[2] <= 0: raise ValueError('Capacité et heures positives requises')
        return 100*v[0]/(v[1]*v[2])
    raise ValueError('Unknown formula')


def calculate_sector(symbol, record, facts, asof):
    family = guidance(symbol,record)['family']
    f = facts if isinstance(facts,dict) else {}
    data = {**(f.get('faits') or {}), **(f.get('sector_faits') or {})}
    period = f.get('exercice_clos') or (f"{f['exercice']}-12-31" if isinstance(f.get('exercice'),int) else None)
    common=() if family in FINANCIAL or family=='Holdings et participations' else COMMON
    if family=='Immobilier - foncières':common=tuple(k for k in COMMON if k in ('operating_margin_pct','group_margin_pct','operating_cash_margin_pct','capex_revenue_pct','free_cash_after_capex_mmad','ebe_margin_pct'))
    selected = common + BY_FAMILY.get(family,())
    if f.get('devise') in MONETARY_UNITS and f.get('devise') != 'MAD':
        selected += ('native_group_roe_closing_pct', 'native_group_roe_average_pct')
    metrics = {}
    for key in selected:
        spec = RULES[key]
        values, inputs, problems = [], {}, []
        currency = f.get('devise', 'MAD')
        native = currency in MONETARY_UNITS and key in NATIVE_MONETARY_RATIOS
        permitted_currency = currency if native else 'MAD'
        if currency != 'MAD' and not native:
            problems.append({'reason':'Sortie monétaire MAD ou unité métier : conversion documentée requise'})
        for field in spec['inputs']:
            fact = data.get(field)
            if not isinstance(fact,dict):
                problems.append({'field':field,'reason':'Donnée publiée absente'});continue
            inputs[field] = dict(fact)
            value = fact.get('valeur')
            expected = str(int(period[:4])-1)+period[4:] if period and field.endswith('_ouverture') else period
            try:
                valid = (not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)
                    and fact.get('validation_status') in REVIEWED
                    and re.fullmatch(r'sha256:[0-9a-f]{64}',str(fact.get('document_hash','')))
                    and isinstance(fact.get('page'),int) and not isinstance(fact['page'],bool) and fact['page']>0
                    and urlsplit(str(fact.get('url',''))).scheme == 'https'
                    and fact.get('period_end') == expected and expected <= asof
                    and fact.get('devise',f.get('devise','MAD')) == permitted_currency
                    and (currency == 'MAD' or fact.get('devise') == currency)
                    and bool(fact.get('base')) and bool(fact.get('unite')))
            except (TypeError,ValueError,OverflowError):
                valid = False
            if not valid: problems.append({'field':field,'reason':'Preuve primaire, date, devise ou valeur non vérifiée'})
            if valid and field in ('capex_decaisse','stocks','creances_exploitation','dettes_exploitation') and value<0:
                problems.append({'field':field,'reason':'Poste attendu positif ou nul ; signe à rapprocher'})
            if valid and fact.get('derivation') is not None:
                try:
                    parts = fact.get('components')
                    if (field != 'charges_generales_exploitation'
                            or fact['derivation'] != 'negated_sum_of_reported_expenses'
                            or not isinstance(parts, list) or len(parts) != 2
                            or not all(isinstance(x, dict) for x in parts)
                            or {x.get('field') for x in parts} != {'general_expenses', 'tangible_intangible_depreciation'}):
                        raise ValueError('Décomposition de charges inconnue')
                    total = Decimal(0)
                    for part in parts:
                        if (any(part.get(k) != fact.get(k) for k in
                                ('devise','base','period_end','url','document_hash','page','unite'))
                                or part.get('unite_au_rapport') != 'KMAD'
                                or isinstance(part.get('valeur_au_rapport'), bool)):
                            raise ValueError('Pièces des composantes non homogènes')
                        raw = Decimal(str(part['valeur_au_rapport']))
                        if not raw.is_finite() or raw > 0:
                            raise ValueError('Charges publiées négatives requises')
                        total -= raw / 1000
                    if fact.get('devise') != 'MAD' or abs(total-Decimal(str(value))) > Decimal('0.000000001'):
                        raise ValueError('Somme des charges non rapprochée')
                except (KeyError, TypeError, ValueError, ArithmeticError):
                    problems.append({'field':field,'reason':'Composantes des charges et somme non rapprochées'})
            if valid and fact.get('valeur_au_rapport') is not None:
                money={'MAD':1,'DH':1,'KMAD':1000,'kMAD':1000,'MMAD':1000000,'MDH':1000000}
                if currency == 'TND' and native:
                    money = {'TND':1, 'KTND':1000, 'MTND':1000000}
                original,target=fact.get('unite_au_rapport'),fact.get('unite')
                scale=(Decimal(money[target])/money[original] if target in money and original in money else Decimal(1) if original==target else None)
                try:
                    raw=Decimal(str(fact['valeur_au_rapport']))
                    if scale is None or not raw.is_finite():raise ValueError('Unité originale inconnue')
                    if fact.get('normalization')=='cash_outflow_to_positive_capex':
                        if field!='capex_decaisse' or raw>0:raise ValueError('Convention de signe incompatible')
                        raw=-raw
                    elif fact.get('normalization')=='expense_to_positive_cost':
                        if field!='cout_des_ventes' or raw>0:raise ValueError('Convention de coût incompatible')
                        raw=-raw
                    elif fact.get('normalization') is not None:
                        raise ValueError('Normalisation inconnue')
                    if abs(raw/scale-Decimal(str(value)))>Decimal('0.000000001'):
                        raise ValueError('Conversion non concordante')
                except (ValueError,ArithmeticError):
                    problems.append({'field':field,'reason':'Montant original, signe et unité normalisée non rapprochés'})
            if spec['definition_contract'] and fact.get('definition_contract') != spec['definition_contract']:
                problems.append({'field':field,'reason':'Définition métier non rapprochée : '+spec['definition_contract']})
            values.append(Decimal(str(value)) if valid else Decimal(0))
        bases = {_basis(x.get('base')) for x in inputs.values()}
        if len(bases)>1: problems.append({'reason':'Périmètres ou normes non identiques'})
        # Monetary inputs must share one explicit currency and scale. Physical
        # formulas and MAD-labelled outputs retain their dimensional contracts.
        dimensional = {'hotel_adr_mad':['MAD','chambres'], 'hotel_revpar_mad':['MAD','chambres'],
            'hotel_occupancy_pct':['chambres','chambres'], 'mine_unit_cost':['MAD','unites'],
            'port_utilization_pct':['unites','unites'], 'electric_capacity_factor_pct':['MWh','MW','heures']}
        monetary_unit = MONETARY_UNITS.get(currency, 'MMAD') if native else 'MMAD'
        units = dimensional.get(key,[monetary_unit]*len(spec['inputs']))
        for field,unit in zip(spec['inputs'],units):
            if field in inputs and inputs[field].get('unite') != unit:
                problems.append({'field':field,'reason':'Unité attendue : '+unit})
        value = None
        if not problems:
            try:
                with localcontext() as c:
                    c.prec=40;value=float(round(_compute(spec['expression'],values),4))
            except (ValueError,ArithmeticError):
                problems.append({'reason':'Dénominateur ou contrat de calcul non pertinent'})
        metrics[key] = dict(value=value,status='available' if value is not None else 'unavailable',
            formula_version=VERSION,formula=formula_text(spec),operation=spec['expression'],label=spec['label'],unit=spec['unit'],
            input_fields=spec['inputs'],inputs=inputs,period_end=period,exercise=f.get('exercice'),
            currency=currency,accounting_basis=f.get('accounting_basis'),
            currency_method='same_currency_ratio_no_fx' if native else 'MAD_or_physical_units',
            currency_conversion_applied=False,
            document_date=f.get('document_date'),document_date_status='documented' if f.get('document_date') else 'not_documented',
            methodology_url=REFERENCES[spec['reference']],notes=spec['note'],reasons=problems,
            used_for_score=False,certified=False)
    # Segments stay separate; never sum their revenue without eliminations.
    segments = {}
    for name,segment in (f.get('segments') or {}).items():
        if isinstance(segment,dict) and not segment.get('segments'):
            segments[name] = calculate_sector(symbol,record,{**segment,'segments':{}},asof)
    return dict(version=VERSION,symbol=symbol,family=family,period_end=period,metrics=metrics,
        segments=segments,published_kpis=published_kpis(data,family,period,asof),used_for_score=False,documents_certified=False,
        published_business_kpis_to_collect=guidance(symbol,record)['metrics_to_verify'])
