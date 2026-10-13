import copy
import json
from pathlib import Path
import unittest

from nour.fundamentals import calculate
from nour.research import peers
from nour.peer_groups import group_for
from tools.reconcile_adi_oct11 import merge, URL

ROOT = Path(__file__).resolve().parents[1]


class SectorQuality(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads((ROOT/'data/facts_reference.json').read_text())

    def test_adi_replay_preserves_semesters_other_titles_and_future_exercises(self):
        before = copy.deepcopy(self.facts)
        after = merge(before)
        self.assertEqual(before, self.facts)
        self.assertEqual(merge(after), after)
        for s, r in before['records'].items():
            self.assertEqual(r.get('latest_report'), after['records'][s].get('latest_report'))
            if s != 'ADI':
                self.assertEqual(r, after['records'][s])
        before['records']['ADI']['exercice'] = 2026
        self.assertEqual(merge(before), before)
        before['records']['ADI']['exercice'] = 2025
        before['records']['ADI']['url'] = 'https://example.org/other.pdf'
        with self.assertRaises(ValueError):
            merge(before)

    def test_adi_exact_growth_and_separate_average_roe(self):
        f = merge(self.facts)['records']['ADI']
        r = calculate({'price':322}, f)
        self.assertEqual(r['revenue_growth_pct'], 2.88)
        self.assertEqual(r['roe_pct'], 10.21)
        self.assertEqual(r['roe_average_equity_pct'], 10.64)
        self.assertEqual(r['eps_mad'], 18.46)
        for change in ({'validation_status':'referenced_import'}, {'document_hash':None},
                       {'base':'social'}, {'period_end':'2023-12-31'}, {'valeur':-10}):
            altered = copy.deepcopy(f)
            altered['faits']['capitaux_propres_part_groupe_2024'].update(change)
            self.assertIsNone(calculate({'price':322}, altered)['roe_average_equity_pct'])
        altered = copy.deepcopy(f)
        for key in ('capitaux_propres_part_groupe', 'capitaux_propres_part_groupe_2024', 'resultat_net_part_groupe'):
            altered['faits'][key]['base'] = None
        self.assertIsNone(calculate({'price':322}, altered)['roe_average_equity_pct'])
        altered = copy.deepcopy(f)
        altered['faits']['resultat_net_part_groupe']['valeur'] = None
        altered['faits']['resultat_net_social'] = {'valeur':100, 'page':22}
        self.assertIsNone(calculate({'price':322}, altered)['roe_average_equity_pct'])

    def test_disputed_debt_is_withheld_with_visible_reconciliation(self):
        for s, calculated, reported in [('ADI',1361.49,1303),('MNG',10933.2,12674),('MUT',989.22,828)]:
            r = calculate({'price':100}, self.facts['records'][s])
            self.assertEqual(r['debt_reconciliation']['status'], 'unresolved')
            self.assertEqual(r['debt_reconciliation']['calculated_mmad'], calculated)
            self.assertEqual(r['debt_reconciliation']['reported_mmad'], reported)
            self.assertIsNone(r['net_debt_strict_mmad'])
            self.assertIsNone(r['net_debt_ebitda'])
        r = calculate({'price':100}, self.facts['records']['MSA'])
        self.assertLess(r['net_debt_strict_mmad'], 0)
        self.assertIsNone(r['net_debt_ebitda'])
        self.assertEqual(r['debt_reconciliation']['status'], 'within_tolerance')
        self.assertEqual(calculate({'price':100}, self.facts['records']['HAL'])['net_debt_ebitda'],5.91)

    def test_zero_reported_debt_is_not_treated_as_missing(self):
        f = copy.deepcopy(self.facts['records']['ADI'])
        f['faits']['endettement_net']['valeur'] = 0
        self.assertEqual(calculate({'price':100},f)['debt_reconciliation']['status'],'unresolved')
        del f['faits']['endettement_net']
        self.assertEqual(calculate({'price':100},f)['debt_reconciliation']['status'],'not_cross_checked')

    def test_known_businesses_are_not_mixed(self):
        for left,right,sector in [('ADI','ARD','Immobilier'),('AFM','WAF','Assurance'),
                                   ('MGL','EQD','Finance'),('CASH','MGL','Finance')]:
            self.assertNotEqual(group_for(left,{'sector':sector})[0],group_for(right,{'sector':sector})[0])
        self.assertEqual(group_for('ADI',{})[0],group_for('ADH',{})[0])

    def test_peer_dates_minimum_exclusion_and_extreme_legitimate_values(self):
        records={str(i):{'sector':'Banque'} for i in range(6)}
        rows=[{'symbol':str(i),'decision':'OBSERVABLE','asof':'2026-10-09',
            'fundamental':{'exercise':2025,'period_end':'2025-12-31','currency':'MAD',
                'accounting_basis':'consolidé IFRS','pe':v,'pb':1,'roe_pct':10}}
            for i,v in enumerate([1000,10,12,14,16,18])]
        rows[-1]['asof']='2026-10-08'
        peers(rows,records)
        m=rows[0]['sector_comparison']['metrics']['pe']
        self.assertEqual(m['median'],13)
        self.assertEqual(m['symbols'],['1','2','3','4'])
        self.assertEqual(m['status'],'available')  # Extreme is not proof of error.
        rows[1]['fundamental']['period_end']='2025-06-30'
        peers(rows,records)
        self.assertIsNone(rows[0]['sector_comparison']['metrics']['pe']['median'])
        rows[0]['asof']=None
        peers(rows,records)
        self.assertIn('Période',rows[0]['sector_comparison']['metrics']['pe']['reason'])


if __name__ == '__main__':
    unittest.main()
