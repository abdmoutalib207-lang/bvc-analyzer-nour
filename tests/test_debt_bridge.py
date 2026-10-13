import copy
import json
from pathlib import Path
import unittest

from nour.fundamentals import calculate
from tools.reconcile_debt_oct13 import merge

ROOT = Path(__file__).resolve().parents[1]


class DebtBridge(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads((ROOT/'data/facts_reference.json').read_text())

    def test_replay_preserves_semesters_others_and_newer_years(self):
        before = copy.deepcopy(self.facts)
        after = merge(before)
        self.assertEqual(before, self.facts)
        self.assertEqual(merge(after), after)
        for s,r in before['records'].items():
            self.assertEqual(r.get('latest_report'), after['records'][s].get('latest_report'))
            if s not in ('ADI','MNG','MUT'):
                self.assertEqual(r,after['records'][s])
        before['records']['MNG']['exercice']=2026
        self.assertEqual(merge(before)['records']['MNG'],before['records']['MNG'])

    def test_mng_bridge_without_double_counting_leases_or_filling_residual(self):
        f=merge(self.facts)['records']['MNG']
        r=calculate({'price':100},f)
        d=r['debt_reconciliation']
        self.assertEqual(d['status'],'scope_reconciled')
        self.assertEqual(r['net_debt_strict_mmad'],10933.2)
        self.assertEqual(r['net_debt_ebitda'],1.83)
        self.assertEqual(d['reported_mmad'],12674.4)
        self.assertEqual(d['bridge']['reconstructed_reported_mmad'],12674.1)
        self.assertEqual(d['bridge']['residual_mmad'],-.3)
        self.assertEqual([c['value_mmad'] for c in d['bridge']['components']],[1707.9,33])
        self.assertEqual(r['roe_average_equity_pct'],27.09)
        self.assertEqual(calculate({'price':100},merge(self.facts)['records']['MUT'])['roe_average_equity_pct'],8.1)
        del f['debt_scope_bridge']
        self.assertEqual(calculate({'price':100},f)['debt_reconciliation']['status'],'unresolved')

    def test_bridge_requires_validated_scope_dates_units_values_and_definition(self):
        f=merge(self.facts)['records']['MNG']
        key='comptes_courants_associes_hors_perimetre_dette'
        for update in ({'valeur':1000},{'valeur':None},{'valeur':True},{'page':None},
                       {'validation_status':'referenced_import'},{'period_end':'2024-12-31'},
                       {'base':None},{'unite':'KMAD'},{'document_hash':'sha256:'+'0'*64},
                       {'url':'https://example.org/unverified.pdf'}):
            x=copy.deepcopy(f);x['faits'][key].update(update)
            r=calculate({'price':100},x)
            self.assertEqual(r['debt_reconciliation']['status'],'unresolved',update)
            self.assertIsNone(r['net_debt_ebitda'])
        for update in ({'component_keys':[]},{'component_keys':[key,key]},
                       {'component_keys':'not-a-list'},{'component_keys':['dettes_financieres']},
                       {'definition':None},{'period_end':'2024-12-31'}):
            x=copy.deepcopy(f);x['debt_scope_bridge'].update(update)
            self.assertEqual(calculate({'price':100},x)['debt_reconciliation']['status'],'unresolved')
        x=copy.deepcopy(f);x['faits']['excedent_brut_exploitation']['period_end']='2024-12-31'
        r=calculate({'price':100},x)
        self.assertEqual(r['debt_reconciliation']['status'],'scope_reconciled')
        self.assertIsNone(r['net_debt_ebitda'])

    def test_residual_uses_absolute_not_percentage_tolerance(self):
        f=merge(self.facts)['records']['MNG']
        f['faits']['endettement_net']['valeur']=12680  # < 2%, but not rounding.
        r=calculate({'price':100},f)
        self.assertEqual(r['debt_reconciliation']['status'],'unresolved')
        self.assertIsNone(r['net_debt_strict_mmad'])


if __name__ == '__main__':
    unittest.main()
