import copy
import unittest

from nour.fundamentals import calculate
from tools.import_bank_oct04 import additions, merge


class BankComplement(unittest.TestCase):
    def test_cih_uses_corrected_group_equity_and_withholds_capital_ratios(self):
        facts = additions()['CIH']
        facts['faits']['nombre_actions_au_rapport'] = dict(valeur=35605624, page=52, unite='actions')
        result = calculate({'price':400}, facts)
        self.assertEqual(result['earnings_mmad'], 1089.362)
        self.assertEqual(result['evidence']['capitaux_propres_part_groupe']['value'], 9768.468)
        self.assertEqual(result['roe_pct'], 11.15)
        self.assertEqual(result['evidence']['nombre_actions_post_augmentation_2026_a_rapprocher']['value'], 38641338)
        self.assertEqual(result['pnb_growth_pct'], 14.41)
        for key in ('eps_mad', 'pe', 'pb', 'book_value_per_share_mad', 'revenue_growth_pct', 'net_debt_ebitda'):
            self.assertIsNone(result[key], key)

    def test_cdm_retains_explicit_group_equity_and_pnb(self):
        result = calculate({'price':1000}, additions()['CDM'])
        self.assertEqual(result['earnings_mmad'], 863.551)
        self.assertEqual(result['evidence']['capitaux_propres_part_groupe']['value'], 8203.010)
        self.assertEqual(result['roe_pct'], 10.53)
        self.assertEqual(result['evidence']['nombre_actions_post_augmentation_2026_a_rapprocher']['value'], 11626499)
        self.assertEqual(result['pnb_growth_pct'], 8.03)
        self.assertEqual(result['semester_activity_label'], 'PNB')
        for key in ('eps_mad', 'pe', 'pb', 'revenue_growth_pct'):
            self.assertIsNone(result[key], key)

    def test_cih_semester_is_separate_from_annual_earnings(self):
        result = calculate({'price':400}, additions()['CIH'])
        semester = result['latest_report']
        self.assertEqual(semester['reported_net_millions'], 616.987)
        self.assertEqual(semester['reported_net_previous_millions'], 615.437)
        self.assertEqual(semester['revenue_millions'], 2825.752)
        self.assertEqual(semester['period_end'], '2026-06-30')
        self.assertEqual(result['earnings_mmad'], 1089.362)
        self.assertEqual(result['semester_activity_label'], 'PNB')

    def test_merge_preserves_existing_semesters_and_is_idempotent(self):
        semester = dict(period_end='2026-06-30', document_url='https://example.org/report.pdf',
                        reported_net_millions=531.692, provenance={'commit':'original'})
        data = dict(records={'CDM':dict(latest_report=semester), 'OTHER':{'untouched':True}})
        original = copy.deepcopy(data)
        once = merge(data)
        self.assertEqual(data, original)
        self.assertEqual(once['records']['CDM']['latest_report'], semester)
        self.assertEqual(once['records']['OTHER'], original['records']['OTHER'])
        self.assertEqual(merge(once), once)
        # A future verified CIH semester must survive replay too.
        once['records']['CIH']['latest_report'] = copy.deepcopy(semester)
        self.assertEqual(merge(once)['records']['CIH']['latest_report'], semester)


if __name__ == '__main__':
    unittest.main()
