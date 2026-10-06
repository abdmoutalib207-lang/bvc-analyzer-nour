import copy
import unittest
from datetime import datetime
from nour.market import CASABLANCA
from nour.overview import update_overview
from nour.market_view import market_panel
from nour.report_contracts import synchronize_market, volume_reconciliation


class OverviewContracts(unittest.TestCase):
    def setUp(self):
        self.history = {'seances': {'2025-12-31': 20000, '2026-10-02': 17000}}
        self.previous = {'current': {'asof': '2026-10-02'},
                         'last_closed': {'asof': '2026-10-02'}}
        self.row = {'Symbol': 'MASI', 'DateCotation': '05/10/2026 13:45:00',
                    'Cours': 17100, 'CoursVeille': 17000, 'PlusHaut': 17200, 'PlusBas': 16900}

    def test_provisional_index_cannot_become_historical_close(self):
        old = copy.deepcopy(self.history)
        overview, hist = update_overview(self.previous, self.history, [self.row], [],
                                        datetime(2026,10,5,13,45,tzinfo=CASABLANCA))
        self.assertEqual(hist, old)
        self.assertEqual(overview['last_closed']['asof'], '2026-10-02')
        self.assertEqual(overview['current']['status'], 'intraday')
        self.assertNotIn('breadth', overview['current'])
        self.assertEqual(self.previous['current']['asof'], '2026-10-02')

    def test_closed_index_and_ytd_are_dated_and_replayable(self):
        now = datetime(2026,10,5,18,tzinfo=CASABLANCA)
        overview, hist = update_overview(self.previous, self.history, [self.row], [],now)
        self.assertEqual(hist['seances']['2026-10-05'], 17100)
        self.assertEqual(overview['last_closed']['masi']['ytd_pct'], -14.5)
        overview2, hist2 = update_overview(overview, hist, [self.row], [],now)
        self.assertEqual(hist, hist2)
        self.assertEqual(overview, overview2)

    def test_wrong_identity_cancelled_future_regression_and_conflict_rejected(self):
        for mutation in ({'Symbol':'BANK'}, {'DateCotation':'17/09/2026'},
                         {'DateCotation':'06/10/2026'}, {'DateCotation':'01/10/2026'},
                         {'DateCotation':'02/10/2026', 'Cours':18000}, {'Cours':float('nan')}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                update_overview(self.previous,self.history,[{**self.row, **mutation}],[],
                                datetime(2026,10,5,18,tzinfo=CASABLANCA))

    def test_summary_cannot_present_other_dates_or_empty_coverage_as_zero(self):
        rows = [{'Symbol': str(i), 'DateDernierCours': '05/10/2026', 'QteEchangee':10,
                 'Volumes':1000, 'VariationP': -1 if i%2 else 1} for i in range(20)]
        rows.append({'Symbol':'OLD','DateDernierCours':'02/10/2026','QteEchangee':999,
                     'Volumes':999999,'VariationP':0})
        overview, _ = update_overview(self.previous,self.history,[self.row],rows,
                                     datetime(2026,10,5,18,tzinfo=CASABLANCA))
        self.assertEqual(overview['current']['breadth'],dict(up=10,down=10,flat=0,quoted=20))
        self.assertEqual(overview['current']['turnover_mad'],20000)
        self.assertNotIn('transactions',overview['current'])

    def test_dated_index_summary_is_preferred_to_subset_aggregation(self):
        row = {**self.row, 'NbrHausse':10, 'NbrBaisse':54, 'NbrInchange':4,
               'NbrValeur':68, 'Volume':258466497.74, 'QteEchange':859537, 'NbrTransaction':5487}
        overview, _ = update_overview(self.previous, self.history, [row], [],
                                     datetime(2026,10,5,18,tzinfo=CASABLANCA))
        current = overview['current']
        self.assertEqual(current['transactions'],5487)
        self.assertEqual(current['breadth']['quoted'],68)
        self.assertEqual(current['turnover_mad'],258466497.74)

    def test_missing_index_has_an_explicit_fallback_and_no_invented_chart(self):
        page = market_panel({'analysis_date':'2026-10-03'})
        self.assertIn('Historique MASI indisponible',page)
        self.assertNotIn('<polyline',page)
        self.assertIn('Bilan de séance indisponible',page)


class VolumeReconciliationContracts(unittest.TestCase):
    def setUp(self):
        self.overview = {'asof': '2026-10-06', 'turnover_mad': 346377516.02,
                         'breadth': {'quoted': 2}, 'observed_at': '2026-10-06T18:37:08Z'}
        self.report = {'analysis_date': '2026-10-06', 'results': [
            {'symbol': 'A', 'asof': '2026-10-06', 'day_shares': 10,
             'day_turnover_mad_actual': 300000000},
            {'symbol': 'B', 'asof': '2026-10-06', 'day_shares': 20,
             'day_turnover_mad_actual': 49551480.02},
            {'symbol': 'OLD', 'asof': '2026-10-05', 'day_shares': 5,
             'day_turnover_mad_actual': 999999}]}

    def test_different_cdg_versions_are_exposed_without_overwriting_either(self):
        before = copy.deepcopy((self.report, self.overview))
        audit = volume_reconciliation(self.report, self.overview)
        self.assertEqual(audit['status'], 'discrepancy')
        self.assertEqual(audit['lines_turnover_mad'], 349551480.02)
        self.assertEqual(audit['difference_mad'], 3173964)
        self.assertEqual(audit['observed_lines'], 2)
        self.assertEqual((self.report, self.overview), before)
        synchronize_market(self.report, self.overview)
        self.assertEqual(self.report['market']['turnover_mad'], 346377516.02)
        self.assertEqual(self.report['market_volume_audit'], audit)
        page = market_panel(self.report)
        self.assertIn('data-volume-reconciliation="discrepancy"', page)
        self.assertIn('3 173 964,00 DH', page)

    def test_updated_summary_matches_only_same_session_actual_turnover(self):
        self.overview['turnover_mad'] = 349551480.02
        synchronize_market(self.report, self.overview)
        self.assertEqual(self.report['market_volume_audit']['status'], 'matched')
        self.assertIn('data-volume-reconciliation="matched"', market_panel(self.report))

    def test_missing_coverage_or_invalid_amount_cannot_be_certified(self):
        for mutation in ('subset', 'missing', 'nan', 'negative', 'duplicate', 'unknown_count'):
            with self.subTest(mutation=mutation):
                report, overview = copy.deepcopy((self.report, self.overview))
                if mutation == 'subset':
                    overview['breadth']['quoted'] = 3
                elif mutation == 'unknown_count':
                    overview['breadth'] = {}
                elif mutation == 'duplicate':
                    report['results'][1]['symbol'] = 'A'
                else:
                    report['results'][1]['day_turnover_mad_actual'] = {
                        'missing': None, 'nan': float('nan'), 'negative': -1}[mutation]
                self.assertEqual(volume_reconciliation(report, overview)['status'], 'incomplete')

    def test_future_or_missing_summary_remains_unavailable(self):
        self.report['analysis_date'] = '2026-10-05'
        synchronize_market(self.report, self.overview)
        self.assertEqual(self.report['market_volume_audit']['status'], 'unavailable')
        self.assertEqual(volume_reconciliation(self.report, {})['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
