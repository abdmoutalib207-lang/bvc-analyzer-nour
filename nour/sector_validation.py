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
