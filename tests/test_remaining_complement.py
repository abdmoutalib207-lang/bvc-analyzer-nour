import copy
import json
import unittest
from pathlib import Path

from nour.fundamentals import calculate
from tools.import_remaining_annual_oct04 import additions as annual, merge as merge_annual
from tools.import_remaining_semesters_oct04 import additions as semesters, merge as merge_semesters


class RemainingComplement(unittest.TestCase):
    def test_group_equity_excludes_minorities_and_special_guarantee_funds(self):
        expected = {'ATW': (69431.269, 15.33, 49.48), 'BCP': (36974.989, 12.18, 22.15),
                    'BMC': (7572.464, 5.74, 32.74), 'BOA': (31794.360, 11.99, None),
                    'SAF': (6062.749, 11.16, None)}
        for symbol, (equity, roe, eps) in expected.items():
            r = calculate({'price':100}, annual()[symbol])
            self.assertEqual(r['evidence']['capitaux_propres_part_groupe']['value'], equity)
            self.assertEqual(r['roe_pct'], roe)
            self.assertEqual(r['eps_mad'], eps)
            self.assertIsNone(r['revenue_growth_pct'])
            self.assertIsNone(r['net_debt_ebitda'])

    def test_fusion_and_capital_changes_do_not_use_historical_equity_per_new_share(self):
        for symbol in ['BOA', 'SAF']:
            f = annual()[symbol]
            f['faits']['nombre_actions'] = {'valeur':9999999, 'page':1}
            r = calculate({'price':100}, f)
            for key in ['eps_mad','pe','pb','book_value_per_share_mad']:
                self.assertIsNone(r[key])
        self.assertEqual(annual()['SAF']['faits']['nombre_actions_post_fusion_2026_a_rapprocher']['valeur'],5341874)

    def test_semester_units_and_perimeters_are_not_mixed_with_annuals(self):
        f = merge_semesters(merge_annual({'records':{}}))['records']['SAF']
        r = calculate({}, f)
        self.assertEqual(r['earnings_mmad'],676.523)
        self.assertEqual(r['latest_report']['reported_net_millions'],-88.608)
        self.assertIn('avant fusion',r['latest_report']['accounting_basis'])
        enk = semesters()['ENK']['latest_report']
        self.assertEqual(enk['currency'],'TND')
        self.assertEqual(enk['reported_net_millions'],29.973162)
        self.assertIn('pro forma',enk['accounting_basis'])
        stk = semesters()['STK']['latest_report']
        self.assertEqual(stk['reported_net_millions'],-7.089)
        self.assertNotEqual(stk['reported_net_millions'],-7.090)
        self.assertIsNone(semesters()['JET']['latest_report']['reported_net_millions'])
        self.assertIn('total publié',semesters()['M2M']['latest_report']['accounting_basis'])

    def test_replays_preserve_every_existing_semester_and_other_records(self):
        original = {'records':{'ATW':{'latest_report':{'period_end':'2027-06-30','keep':True,'provenance':{'commit':'future'}}},
                               'MDP':{'latest_report':{'keep':True}}, 'OTHER':{'keep':True}}}
        before = copy.deepcopy(original)
        once = merge_semesters(merge_annual(original))
        self.assertEqual(original,before)
        for symbol in ['ATW','MDP','OTHER']:
            key = 'latest_report' if symbol != 'OTHER' else 'keep'
            self.assertEqual(once['records'][symbol][key],before['records'][symbol][key])
        self.assertEqual(merge_semesters(merge_annual(once)),once)

    def test_principal_snapshot_distinguishes_periods_and_denominators(self):
        p = Path(__file__).resolve().parents[1] / 'docs/comparisons/2026-10-04-principal.json'
        d = json.loads(p.read_text())['records']
        for symbol in ['MGL','MRL','ATW','BCP','BMC']:
            self.assertEqual(d[symbol]['principal_eps_annual_mad'],d[symbol]['nour_eps_annual_mad'])
        self.assertEqual(d['CDM']['principal_eps_annual_mad'],74.27)
        self.assertIsNone(d['CDM']['nour_eps_annual_mad'])
        self.assertEqual(d['CIH']['principal_roe_annual_pct'],11.1)
        self.assertEqual(d['CIH']['nour_roe_annual_pct'],11.15)
        self.assertEqual(d['MGL']['principal_eps_ttm_mad'],115.03)


if __name__ == '__main__':
    unittest.main()
