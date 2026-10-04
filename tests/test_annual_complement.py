import copy
import unittest

from nour.fundamentals import calculate
from tools.import_annual_oct04_complement import additions, merge


class AnnualComplement(unittest.TestCase):
    def test_maghrebail_detailed_equity_and_financial_pnb(self):
        r = calculate({'price':1000}, additions()['MGL'])
        self.assertEqual(r['eps_mad'], 107.07)
        self.assertEqual(r['book_value_per_share_mad'], round(1228.220e6/1384182, 2))
        self.assertEqual(r['roe_pct'], 12.07)
        self.assertEqual(r['pnb_growth_pct'], 16.09)
        self.assertIsNone(r['revenue_growth_pct'])
        self.assertIsNone(r['net_debt_ebitda'])

    def test_maroc_leasing_excludes_subordinated_debt(self):
        r = calculate({'price':365}, additions()['MRL'])
        self.assertEqual(r['eps_mad'], 38.64)
        self.assertEqual(r['book_value_per_share_mad'], round(1227.913e6/2776768, 2))
        self.assertEqual(r['roe_pct'], 8.74)
        self.assertEqual(r['pnb_growth_pct'], 2.11)
        self.assertEqual(r['semester_activity_label'], 'PNB')
        self.assertIsNone(r['revenue_growth_pct'])

    def test_med_paper_uses_annual_totals_and_corroborated_share_count(self):
        r = calculate({'price':20}, additions()['MDP'])
        self.assertEqual(r['earnings_mmad'], 6.71310550)
        self.assertEqual(r['eps_mad'], 1.40)
        self.assertEqual(r['roe_pct'], 16.32)
        self.assertEqual(r['revenue_growth_pct'], -16.25)
        e = r['evidence']['nombre_actions_au_rapport']
        self.assertEqual(e['value'], 4783823)
        self.assertEqual(e['page'], 1)
        self.assertTrue(e['document_url'].endswith('CP_Med_Paper_T4_2025.pdf'))
        self.assertEqual(r['evidence']['resultat_net_social']['original_unit'], 'MAD')
        self.assertTrue(any('perte d’exploitation' in w for w in r['warnings']))

    def test_cash_plus_minority_and_capital_conflicts_stay_unavailable(self):
        f = additions()['CASH']
        # Even accidental addition of a closing denominator must not bypass the block.
        f['faits']['nombre_actions_au_rapport'] = dict(valeur=24553090, page=76, unite='actions')
        r = calculate({'price':250}, f)
        self.assertEqual(r['earnings_mmad'], 242.296)
        self.assertEqual(r['pnb_mmad'], 863.27)
        self.assertEqual(r['evidence']['produit_net_bancaire']['value'], 863.267)
        self.assertEqual(r['pnb_growth_pct'], 13.61)
        for key in ('eps_mad','pe','pb','roe_pct','net_debt_ebitda','revenue_growth_pct'):
            self.assertIsNone(r[key], key)
        self.assertIn('capitaux_propres_part_groupe_a_rapprocher', r['evidence'])
        self.assertEqual(r['semester_activity_label'], 'PNB')

    def test_batch_preserves_semester_values_provenance_and_other_records_on_replay(self):
        semester = dict(period_end='2026-06-30', document_url='https://example.org/semester.pdf',
                        reported_net_millions=12, revenue_millions=40)
        old_provenance = dict(repository='semester-origin', commit='source-sha')
        untouched = dict(url='https://example.org/other.pdf', faits={'old':'value'})
        data = dict(records={'MGL':dict(latest_report=copy.deepcopy(semester), provenance=old_provenance),
                             'MRL':dict(latest_report={**semester, 'provenance':{'commit':'independent'}}),
                             'OTHER':untouched})
        original = copy.deepcopy(data)
        once = merge(data)
        self.assertEqual(data, original)
        self.assertEqual(once['records']['OTHER'], untouched)
        recent = copy.deepcopy(once['records']['MGL']['latest_report'])
        self.assertEqual(recent.pop('provenance'), old_provenance)
        self.assertEqual(recent, semester)
        self.assertEqual(once['records']['MRL']['latest_report'], original['records']['MRL']['latest_report'])
        self.assertEqual(merge(once), once)


if __name__ == '__main__':
    unittest.main()
