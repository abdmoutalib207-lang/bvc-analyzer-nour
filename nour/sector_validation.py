"""Independent rational arithmetic of exported sector calculations, not PDF certification."""
from fractions import Fraction
from math import isfinite


def audit_sector_calculations(report):
    checks=0;failures=[]
    def visit(symbol,block):
        nonlocal checks
        for key,m in block.get('metrics',{}).items():
            if m.get('value') is None:continue
            checks+=1
            try:
                v=[Fraction(str(m['inputs'][f]['valeur'])) for f in m['input_fields']]
                if any(m['inputs'][f].get('devise', m.get('currency', 'MAD')) != m.get('currency', 'MAD')
                       for f in m['input_fields']):
                    raise ValueError('Input/output currency mismatch')
                for field in m['input_fields']:
                    fact=m['inputs'][field]
                    if fact.get('derivation') == 'negated_sum_of_reported_expenses':
                        parts=fact['components']
                        if (len(parts) != 2 or any(p.get('unite_au_rapport') != 'KMAD' for p in parts)
                                or -sum(Fraction(str(p['valeur_au_rapport'])) for p in parts)/1000
                                   != Fraction(str(fact['valeur']))):
                            raise ValueError('Expense component arithmetic mismatch')
                # Independent currency boundary: TND may cancel in a monetary
                # ratio, but must never be exported as a MAD amount or mixed
                # with another currency/scale, even with plausible arithmetic.
                if m.get('currency') == 'TND':
                    if (m.get('unit') not in ('%', '×')
                            or m.get('currency_method') != 'same_currency_ratio_no_fx'
                            or m.get('currency_conversion_applied') is not False
                            or m.get('operation') not in ('ratio', 'ratio100', 'ratio_average', 'ratio_average100', 'working_capital_ratio', 'sum_ratio100')
                            or any(m['inputs'][f].get('devise') != 'TND'
                                   or m['inputs'][f].get('unite') != 'MTND'
                                   for f in m['input_fields'])):
                        raise ValueError('Foreign monetary ratio contract mismatch')
                op=m['operation']
                if op=='ratio':expected=v[0]/v[1]
                elif op=='ratio100':expected=100*v[0]/v[1]
                elif op=='ratio_average':expected=2*v[0]/(v[1]+v[2])
                elif op=='ratio_average100':expected=200*v[0]/(v[1]+v[2])
                elif op=='subtract':expected=v[0]-v[1]
                elif op=='working_capital':expected=v[0]+v[1]-v[2]
                elif op=='working_capital_ratio':expected=100*(v[0]+v[1]-v[2])/v[3]
                elif op=='sum_ratio100':expected=100*(v[0]+v[1])/v[2]
                elif op=='capacity_factor':expected=100*v[0]/(v[1]*v[2])
                else:raise ValueError('Operation unknown')
                if (m.get('used_for_score') is not False or m.get('certified') is not False
                        or not isfinite(m['value']) or abs(Fraction(str(m['value']))-expected)>Fraction('0.00005001')):
                    raise ValueError('Independent disagreement')
            except (ValueError,TypeError,KeyError,ZeroDivisionError,OverflowError):
                failures.append(dict(symbol=symbol,metric=key,actual=m.get('value'),reason='Independent sector arithmetic/contract mismatch'))
        for segment in block.get('segments',{}).values():visit(symbol,segment)
    for row in report['results']:visit(row['symbol'],row.get('sector_indicators') or {})
    return dict(version='nour-sector-arithmetic-v1',arithmetic_checks=checks,failures=failures,documents_certified=False)
