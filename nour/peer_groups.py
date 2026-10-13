"""Nour comparison groups, separate from the exchange's broad sector labels.

Targeted splits, documented in docs/sector-quality-2026-10-11.md. Other sectors
remain explicitly broad: this registry is not a complete business taxonomy.
No Simply Wall St taxonomy, scores or market data are imported.
"""

GROUPS = {
    'Promoteurs immobiliers': ('ADI', 'ADH', 'RDS'),
    'Foncières locatives': ('ARD', 'IMI', 'BAL'),
    'Assureurs': ('WAF', 'ATL', 'SAF'),
    'Courtiers en assurance': ('AFM', 'AGM'),
    'Crédit-bail': ('MRL', 'MGL'),
    'Crédit à la consommation': ('SLM', 'EQD', 'DIS'),
    'Services de paiement': ('CASH',),
    'Holdings diversifiées': ('DHO',),
    'Participations et actifs immobiliers': ('REB',),
}


def group_for(symbol, record):
    for label, symbols in GROUPS.items():
        if symbol in symbols:
            return label, 'business_family'
    return record.get('sector'), 'broad_sector'
